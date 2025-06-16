
use("park-net")

db.requests.remove({})

db.users.find({"cc": "0000000000"})
// Colección: users (corregida)
// db.users.insertMany([
//     {
//         "_id": ObjectId("666c8a7f7b1e3e4d5f6a2b1c"),
//         "full_name": "Juan David Pérez",
//         "cc": "1193597666",
//         "email": "juan.perez@email.com",
//         "hashed_password": "12345",
//         "apartment": "Torre 2, Apto 101",
//         "phone_number": "+573001234567",
//         "role": "residente",
//         "status": "pending_approval",
//     },
//     {
//         "_id": ObjectId("777d8b8e8c2f4e5a6b7c8d9e"),
//         "full_name": "Admin Principal",
//         "cc": "1193597668",
//         "email": "admin@condominio.com",
//         "hashed_password": "12345",
//         "apartment": "Oficina Administración",
//         "phone_number": "+573009876543",
//         "role": "administrador",
//         "status": "active",
//     },
//     {
//         "_id": ObjectId("888e8f9a0b1c2d3e4f5a6b7c"),
//         "full_name": "María García",
//         "cc": "1193597669",
//         "email": "maria.garcia@email.com",
//         "hashed_password": "12345",
//         "apartment": "Torre 1, Apto 302",
//         "phone_number": "+573002233445",
//         "role": "residente",
//         "status": "active",
//         "vehicle_slots": {
//             "carro": {"available": false, "request_id": ObjectId("999f0a1b2c3d4e5f6a7b8c9d")},
//             "moto": {"available": true, "request_id": null}
//         },
//     }
// ]);

// // Colección: requests (corregida)
// db.requests.insertMany([
//     {
//         "_id": ObjectId("111a2b3c4d5e6f7a8b9c0d1e"),
//         "user_id": ObjectId("666c8a7f7b1e3e4d5f6a2b1c"),
//         "vehicle_type": "carro",
//         "license_plate": "ABC123",
//         "description": "descripcion",
//         "disability": false,
//         "pay": true,
//         "status": "pending",
//         "lottery_period": "2025-07"
//     },
//     {
//         "_id": ObjectId("222b3c4d5e6f7a8b9c0d1e2f"),
//         "user_id": ObjectId("888e8f9a0b1c2d3e4f5a6b7c"),
//         "vehicle_type": "moto",
//         "license_plate": "XYZ789",
//         "status": "approved",
//         "lottery_period": "2025-07"
//     },
//     {
//         "_id": ObjectId("333c4d5e6f7a8b9c0d1e2f3a"),  // Cambiado 'g' por 'a'
//         "user_id": ObjectId("666c8a7f7b1e3e4d5f6a2b1c"),
//         "vehicle_type": "moto",
//         "license_plate": "MOT001",
//         "status": "rejected",
//         "lottery_period": "2025-07"
//     }
// ]);

// // Colección: lotteries (corregida)
// db.lotteries.insertMany([
//     {
//         "_id": ObjectId("444d5e6f7a8b9c0d1e2f3a4b"),  // Corregido
//         "period": "2025-06",
//         "participants": [
//             {
//                 "user_id": ObjectId("888e8f9a0b1c2d3e4f5a6b7c"),
//                 "full_name": "María García",
//                 "apartment": "Torre 1, Apto 302",
//                 "spot": "A-15",
//                 "vehicle_type": "carro"
//             },
//             {
//                 "user_id": ObjectId("555e6f7a8b9c0d1e2f3a4b5c"),  // Corregido
//                 "full_name": "Carlos Rodríguez",
//                 "apartment": "Torre 3, Apto 501",
//                 "spot": "M-07",
//                 "vehicle_type": "moto"
//             }
//         ],
//         "winners": [
//             {
//                 "user_id": ObjectId("888e8f9a0b1c2d3e4f5a6b7c"),
//                 "full_name": "María García",
//                 "apartment": "Torre 1, Apto 302",
//                 "spot": "A-15",
//                 "vehicle_type": "carro"
//             },
//             {
//                 "user_id": ObjectId("555e6f7a8b9c0d1e2f3a4b5c"),
//                 "full_name": "Carlos Rodríguez",
//                 "apartment": "Torre 3, Apto 501",
//                 "spot": "M-07",
//                 "vehicle_type": "moto"
//             }
//         ],
//         "executed_at": new Date("2025-05-31T18:00:00Z")
//     },
//     {
//         "_id": ObjectId("555e6f7a8b9c0d1e2f3a4b5c"),  // Corregido
//         "period": "2025-07",
//         "participants": [],
//         "winners": [],
//         "executed_at": null
//     }
// ]);