db = db.getSiblingDB('campusnow');

db.createCollection('lectures');
db.createCollection('rooms');
db.createCollection('studiengaenge');
db.createCollection('image_metadata');

// Create indexes for better performance
db.lectures.createIndex({ "room_id": 1 });
db.lectures.createIndex({ "studiengang_id": 1 });
db.lectures.createIndex({ "start_time": 1, "end_time": 1 });
db.lectures.createIndex({ "lecture_id": 1 }, { unique: true });

db.rooms.createIndex({ "room_number": 1 }, { unique: true });
db.rooms.createIndex({ "floor": 1 });

db.studiengaenge.createIndex({ "code": 1 }, { unique: true });

db.image_metadata.createIndex({ "room_id": 1 });
db.image_metadata.createIndex({ "uploaded_at": -1 });

print("✓ Database initialized successfully");
