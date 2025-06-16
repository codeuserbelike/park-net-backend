import os
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Literal # Asegúrate de importar Literal
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

import resend

from app.modules.sorteo.models import LotteryResult, LotteryParticipantResult
from app.modules.sorteo.schemas import LotteryCreate, MyAssignmentOut
from app.modules.solicitudes.models import Request
from app.modules.residentes.models import User
from app.shared.repository import BaseRepository


RESEND_KEY = os.getenv('RESEND_KEY')
if not RESEND_KEY:
    raise RuntimeError("La variable de entorno RESEND_KEY no está configurada.")
resend.api_key = RESEND_KEY

class LotteryService:
    """
    Servicio de lógica de negocio para la gestión de sorteos de parqueo.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.lottery_repository = BaseRepository(self.db["lotteries"], LotteryResult)
        self.request_repository = BaseRepository(self.db["requests"], Request)
        self.user_repository = BaseRepository(self.db["users"], User)  # Para consultar usuarios

    async def _get_previous_period_non_winners(self, current_period: str) -> List[str]:
        """
        Método auxiliar para obtener los user_id de los no ganadores del período anterior.
        El formato de período es 'YYYY-MM'.
        """
        year, month = map(int, current_period.split('-'))
        
        # Calcular el período anterior
        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year
        
        previous_period = f"{prev_year:04d}-{prev_month:02d}"
        
        previous_lottery = await self.lottery_repository.find_one({"period": previous_period})
        
        if previous_lottery and previous_lottery.non_winners:
            # Retorna una lista de user_ids de los no ganadores del periodo anterior
            return [p.user_id for p in previous_lottery.non_winners]
        return []

    async def _generate_spots(self, num_car_spots: int, num_moto_spots: int) -> Dict[str, List[str]]:
        """
        Genera una lista de identificadores de spots de parqueo simulados.
        Ej: C-01, C-02... M-01, M-02...
        """
        car_spots = [f"C-{i+1:02d}" for i in range(num_car_spots)]
        moto_spots = [f"M-{i+1:02d}" for i in range(num_moto_spots)]
        return {"automovil": car_spots, "motocicleta": moto_spots}

    async def execute_lottery(self, lottery_data: LotteryCreate) -> LotteryResult:
        """
        Ejecuta el sorteo de parqueo para un período dado.
        """
        existing_lottery = await self.lottery_repository.find_one({"period": lottery_data.period})
        if existing_lottery:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya se ha ejecutado un sorteo para el período {lottery_data.period}. ID: {existing_lottery.id}"
            )
        
        accepted_requests = await self.request_repository.find_many(
            {"lottery_period": lottery_data.period, "status": "accepted"},
            limit=1000
        )

        if not accepted_requests:
            new_lottery_result = LotteryResult(
                period=lottery_data.period,
                total_car_spots_offered=lottery_data.num_car_spots,
                total_moto_spots_offered=lottery_data.num_moto_spots,
                winners=[],
                non_winners=[],
                executed_at=datetime.utcnow()
            ) # type: ignore
            created_lottery = await self.lottery_repository.create(new_lottery_result)
            return created_lottery

        previous_non_winners_ids = await self._get_previous_period_non_winners(lottery_data.period)
        requests_with_user_info = []
        user_cache: Dict[str, User] = {}

        for req in accepted_requests:
            if str(req.user_id) not in user_cache:
                user_obj = await self.user_repository.get(str(req.user_id))
                if not user_obj:
                    print(f"Advertencia: Usuario con ID {req.user_id} no encontrado para la solicitud {req.id}")
                    continue
                user_cache[str(req.user_id)] = user_obj
            user = user_cache[str(req.user_id)]
            requests_with_user_info.append({
                "request": req,
                "user": user,
                "priority_score": 0
            })
        
        for item in requests_with_user_info:
            req = item["request"]
            user = item["user"]
            if req.disability:
                item["priority_score"] += 1000
            if str(user.id) in previous_non_winners_ids:
                item["priority_score"] += 500
            if req.pay:
                item["priority_score"] += 100
        
        requests_with_user_info.sort(key=lambda x: x["priority_score"], reverse=True)
        from itertools import groupby
        grouped_requests = []
        for score, group in groupby(requests_with_user_info, key=lambda x: x["priority_score"]):
            group_list = list(group)
            random.shuffle(group_list)
            grouped_requests.extend(group_list)
        final_sorted_requests = grouped_requests

        available_spots = await self._generate_spots(lottery_data.num_car_spots, lottery_data.num_moto_spots)
        car_spots = available_spots["automovil"]
        moto_spots = available_spots["motocicleta"]
        
        winners: List[LotteryParticipantResult] = []
        non_winners: List[LotteryParticipantResult] = []
        assigned_users_and_vehicle_types = set()

        for item in final_sorted_requests:
            req = item["request"]
            user = item["user"]
            assignment_key = f"{str(user.id)}_{req.vehicle_type}"
            if assignment_key in assigned_users_and_vehicle_types:
                non_winners.append(LotteryParticipantResult(
                    user_id=str(user.id),
                    cc=user.cc,
                    full_name=user.full_name,
                    apartment=user.apartment,
                    vehicle_type=req.vehicle_type,
                    license_plate=req.license_plate,
                    spot=None,
                    request_id=str(req.id)
                ))
                continue

            spot_assigned = None
            if req.vehicle_type == "automovil" and car_spots:
                spot_assigned = car_spots.pop(0)
            elif req.vehicle_type == "motocicleta" and moto_spots:
                spot_assigned = moto_spots.pop(0)
            
            if spot_assigned:
                winners.append(LotteryParticipantResult(
                    user_id=str(user.id),
                    cc=user.cc,
                    full_name=user.full_name,
                    apartment=user.apartment,
                    vehicle_type=req.vehicle_type,
                    license_plate=req.license_plate,
                    spot=spot_assigned,
                    request_id=str(req.id)
                ))
                assigned_users_and_vehicle_types.add(assignment_key)
            else:
                non_winners.append(LotteryParticipantResult(
                    user_id=str(user.id),
                    cc=user.cc,
                    full_name=user.full_name,
                    apartment=user.apartment,
                    vehicle_type=req.vehicle_type,
                    license_plate=req.license_plate,
                    spot=None,
                    request_id=str(req.id)
                ))
        
        new_lottery_result = LotteryResult(
            period=lottery_data.period,
            total_car_spots_offered=lottery_data.num_car_spots,
            total_moto_spots_offered=lottery_data.num_moto_spots,
            winners=winners,
            non_winners=non_winners,
            executed_at=datetime.utcnow()
        ) # type: ignore
        
        created_lottery = await self.lottery_repository.create(new_lottery_result)
        await self._send_lottery_notifications(created_lottery, notify_non_winners=True)

        return created_lottery

    async def get_lottery_result(
        self, 
        lottery_period: str, 
        vehicle_type: Optional[Literal["automovil", "motocicleta"]] = None # Agregamos el nuevo parámetro
    ) -> LotteryResult:
        """
        Obtiene los resultados de un sorteo por su período, opcionalmente filtrando a los ganadores por tipo de vehículo.
        """
        lottery_result = await self.lottery_repository.find_one({"period": lottery_period})
        if not lottery_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resultado de sorteo no encontrado para el período especificado.")
        
        # Aplicar el filtro si se proporciona un vehicle_type
        if vehicle_type:
            lottery_result.winners = [winner for winner in lottery_result.winners if winner.vehicle_type == vehicle_type]
            # No es necesario filtrar non_winners, ya que la solicitud era para filtrar los GANADORES.
        
        return lottery_result

    async def get_my_assignment(
        self,
        user_id: str,
        lottery_period: str
    ) -> List[MyAssignmentOut]:
        """
        Consulta si un usuario específico tiene parqueadero asignado para un período dado.
        Retorna una lista de asignaciones (puede ser carro y moto).
        """
        lottery_result = await self.lottery_repository.find_one({"period": lottery_period})
        if not lottery_result:
            return []  # Si no hay sorteo para el período, no hay asignaciones

        my_assignments: List[MyAssignmentOut] = []
        for winner in lottery_result.winners:
            if winner.user_id == user_id:
                my_assignments.append(MyAssignmentOut(
                    period=lottery_period,
                    vehicle_type=winner.vehicle_type,
                    license_plate=winner.license_plate,
                    spot=winner.spot,
                ))
        return my_assignments


    async def delete_lottery_result(self, lottery_period: str) -> Dict[str, str]:
        """
        Elimina un sorteo de parqueo por su período.
        """
        # 1. Buscar el sorteo por el período
        lottery_to_delete = await self.lottery_repository.find_one({"period": lottery_period})
        
        if not lottery_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Sorteo no encontrado para el período especificado."
            )
        
        # 2. Si se encuentra, eliminarlo por su ID
        # Asegúrate de que lottery_to_delete.id sea un string para el método delete
        delete_result = await self.lottery_repository.delete(str(lottery_to_delete.id))
        
        # Aunque delete_result.deleted_count debería ser 1 si se encontró y eliminó,
        # la verificación de not lottery_to_delete ya cubre el caso 404.
        # Podríamos añadir una verificación extra aquí si delete_result.deleted_count fuera 0
        # en un escenario inesperado (ej. fue eliminado por otra operación justo después de find_one).
        if not delete_result:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo eliminar el sorteo a pesar de haberlo encontrado. Inténtalo de nuevo."
            )
        return {"message": "Sorteo eliminado exitosamente."}

    async def _send_lottery_notifications(
        self,
        lottery_result: LotteryResult,
        notify_non_winners: bool = False
    ):
        """
        Envía notificaciones por correo a los ganadores y opcionalmente a los no ganadores
        usando Resend. Los ganadores reciben un correo personalizado con su spot asignado.
        """
        print(f"\n--- Preparando Notificaciones Sorteo Período {lottery_result.period} ---")

        def _send_email(to_email: str, subject: str, html_body: str):
            params: resend.Emails.SendParams = {
                "from": "Park-Net Notificaciones <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": html_body
            }
            try:
                result = resend.Emails.send(params)
                msg_id = result.get("id", "—")
                print(f"✅ Correo enviado a {to_email} (id={msg_id})")
            except Exception as e:
                print(f"❌ Error al enviar correo a {to_email}: {e}")

        # Notificar a ganadores
        for winner in lottery_result.winners:
            user = await self.user_repository.get(winner.user_id)
            if not user or not user.email:
                print(f"⚠️ No se pudo enviar correo a {winner.full_name}: email no disponible.")
                continue

            html = f"""
            <html>
            <body>
                <h1>¡Felicidades, {winner.full_name}!</h1>
                <p>Has ganado un espacio de parqueo para tu {winner.vehicle_type}
                (placa {winner.license_plate}) en el período {lottery_result.period}.</p>
                <p>Tu spot asignado es: <strong>{winner.spot}</strong>.</p>
                <p>Por favor, respeta las normas del condominio.</p>
            </body>
            </html>
            """
            _send_email(
                to_email=user.email,
                subject=f"¡Has ganado un spot! – Período {lottery_result.period}",
                html_body=html
            )

        # Notificar a no ganadores (opcional)
        if notify_non_winners:
            for loser in lottery_result.non_winners:
                user = await self.user_repository.get(loser.user_id)
                if not user or not user.email:
                    print(f"⚠️ No se pudo enviar correo a {loser.full_name}: email no disponible.")
                    continue

                html = f"""
                <html>
                <body>
                    <h1>Resultado Sorteo – {loser.full_name}</h1>
                    <p>Lamentablemente no obtuviste un spot para tu {loser.vehicle_type}
                    (placa {loser.license_plate}) en el período {lottery_result.period}.</p>
                    <p>¡Tendrás prioridad en el próximo sorteo!</p>
                </body>
                </html>
                """
                _send_email(
                    to_email=user.email,
                    subject=f"Resultado Sorteo – Período {lottery_result.period}",
                    html_body=html
                )

        print("--- Notificaciones Completadas ---")