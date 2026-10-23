"""Seed sample laboratory equipment items into the database."""

from app import create_app, db
from app.models import Equipment

SAMPLE_EQUIPMENT = [
    {
        "name": "Digital Storage Oscilloscope (100 MHz)",
        "category": "Electronics",
        "description": "Rigol DS1054Z 4-channel digital oscilloscope with 1 GSa/s real-time sample rate and 24 Mpts memory depth.",
        "status": Equipment.STATUS_AVAILABLE,
    },
    {
        "name": "Dual-Channel Bench Power Supply (30V / 5A)",
        "category": "Electronics",
        "description": "Linear DC regulated power supply with dual independent outputs, fine voltage and current adjustment.",
        "status": Equipment.STATUS_AVAILABLE,
    },
    {
        "name": "Compound Optical Microscope (1000x)",
        "category": "Optical Instruments",
        "description": "Binocular optical laboratory microscope with 4x, 10x, 40x, and 100x oil immersion objective lenses and LED illumination.",
        "status": Equipment.STATUS_AVAILABLE,
    },
    {
        "name": "Digital Benchtop Centrifuge",
        "category": "BioLab",
        "description": "High-speed clinical centrifuge (up to 14,000 RPM) with 12-place rotor for 1.5/2.0 mL microcentrifuge tubes.",
        "status": Equipment.STATUS_OUT_OF_SERVICE,
    },
    {
        "name": "Precision Analytical Balance (0.1 mg)",
        "category": "Measurement",
        "description": "Electronic analytical balance with 220g capacity, 0.1mg readability, internal calibration, and draft shield.",
        "status": Equipment.STATUS_AVAILABLE,
    },
    {
        "name": "Arduino & Sensor Starter Kit",
        "category": "Kits",
        "description": "Complete microcontroller experiment kit including Arduino Uno, breadboard, jumper wires, and 37 sensor modules.",
        "status": Equipment.STATUS_AVAILABLE,
    },
    {
        "name": "Thermal Imaging Camera",
        "category": "Optical Instruments",
        "description": "Handheld infrared thermal camera for PCB temperature profiling and thermal inspection. Awaiting sensor recalibration.",
        "status": Equipment.STATUS_OUT_OF_SERVICE,
    },
]


def seed():
    app = create_app()
    with app.app_context():
        added_count = 0
        for item_data in SAMPLE_EQUIPMENT:
            existing = Equipment.query.filter_by(name=item_data["name"]).first()
            if not existing:
                equipment = Equipment(**item_data)
                db.session.add(equipment)
                added_count += 1
        db.session.commit()
        print(f"Seeded {added_count} new equipment items into the database.")
        print(f"Total equipment in database: {Equipment.query.count()}")


if __name__ == "__main__":
    seed()
