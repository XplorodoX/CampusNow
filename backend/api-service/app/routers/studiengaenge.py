"""Studiengaenge (courses) router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.studiengang import StuDiengangResponse
from app.utils import serialize_doc, serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/studiengaenge", tags=["studiengaenge"])


def _serialize_studiengang_document(document: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB-specific values into API-friendly primitives."""
    if "_id" in document:
        document["_id"] = str(document["_id"])
    document.setdefault("semesters", [])
    document.setdefault("related_courses", [])
    return document


def _related_courses(db: Any, program_code: str, exclude_code: str) -> list[dict]:
    """Return all courses with the same program_code, excluding the current one."""
    if not program_code:
        return []
    docs = db.studiengaenge.find(
        {"program_code": program_code, "code": {"$ne": exclude_code}},
        {"_id": 1, "name": 1, "code": 1, "semesters": 1},
    )
    return [
        {"_id": str(d["_id"]), "name": d.get("name"), "code": d.get("code"), "semesters": d.get("semesters", [])}
        for d in docs
    ]


@router.get(
    "",
    response_model=list[StuDiengangResponse],
    summary="Alle Studiengänge abrufen",
    response_description="Liste aller verfügbaren Studiengänge",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "_id": "INF-B-6",
                            "name": "Informatik Sem. 1+2",
                            "code": "INF S1+2",
                            "semesters": [1, 2],
                            "program_code": "INF",
                            "program_name": "Bachelor Informatik",
                            "lecture_count": 12,
                            "last_scraped": "2024-04-15T06:00:00",
                            "created_at": "2024-01-01T00:00:00",
                            "related_courses": [
                                {"_id": "INF-B-34", "name": "Informatik Sem. 3+4", "code": "INF S3+4", "semesters": [3, 4]}
                            ],
                        }
                    ]
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_studiengaenge() -> list[StuDiengangResponse]:
    """Gibt alle Studiengänge zurück, die im STARplan-System der HS Aalen hinterlegt sind."""
    try:
        db = mongo_client.get_db()
        all_docs = list(db.studiengaenge.find())

        # Build program_code → other courses lookup in one pass
        by_program: dict[str, list[dict]] = {}
        for doc in all_docs:
            pc = doc.get("program_code")
            if pc:
                by_program.setdefault(pc, []).append(doc)

        result = []
        for doc in all_docs:
            doc = _serialize_studiengang_document(doc)
            pc = doc.get("program_code")
            if pc and pc in by_program:
                doc["related_courses"] = [
                    {"_id": str(d["_id"]), "name": d.get("name"), "code": d.get("code"), "semesters": d.get("semesters", [])}
                    for d in by_program[pc]
                    if str(d["_id"]) != doc["_id"]
                ]
            result.append(doc)

        return result

    except Exception as e:
        logger.error(f"Error fetching Studiengänge: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/by-program/{program_code}",
    response_model=list[StuDiengangResponse],
    summary="Alle Semester-Gruppen eines Studiengangs abrufen",
    response_description="Alle Einträge mit demselben program_code (verschiedene Semester)",
    responses={
        404: {"description": "Kein Studiengang mit diesem program_code gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_studiengaenge_by_program(program_code: str) -> list[StuDiengangResponse]:
    """Gibt alle Semester-Gruppen zurück, die zum gleichen Studiengang gehören.

    Nützlich wenn z. B. 'INF S1+2', 'INF S3+4' und 'INF S5+6' zum
    Studiengang 'INF' gehören und gemeinsam angezeigt werden sollen.
    """
    try:
        db = mongo_client.get_db()
        docs = list(db.studiengaenge.find({"program_code": program_code}))

        if not docs:
            raise HTTPException(status_code=404, detail="No courses found for this program_code")

        result = []
        for doc in docs:
            doc = _serialize_studiengang_document(doc)
            doc["related_courses"] = [
                {"_id": str(d["_id"]), "name": d.get("name"), "code": d.get("code"), "semesters": d.get("semesters", [])}
                for d in docs
                if str(d["_id"]) != doc["_id"]
            ]
            result.append(doc)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching courses for program {program_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{studiengang_id}",
    response_model=StuDiengangResponse,
    summary="Einzelnen Studiengang abrufen",
    response_description="Der gefundene Studiengang inkl. verwandter Semester-Gruppen",
    responses={
        404: {"description": "Studiengang nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_studiengang(studiengang_id: str) -> StuDiengangResponse:
    """Gibt einen einzelnen Studiengang anhand seiner ID zurück.

    Das Feld `related_courses` enthält alle anderen Semester-Gruppen
    des gleichen Studiengangs (gleicher `program_code`).
    """
    try:
        db = mongo_client.get_db()
        studiengang = db.studiengaenge.find_one({"_id": studiengang_id})

        if not studiengang:
            raise HTTPException(status_code=404, detail="Studiengang not found")

        doc = _serialize_studiengang_document(studiengang)
        doc["related_courses"] = _related_courses(db, doc.get("program_code"), doc.get("code", ""))
        return doc

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Studiengang: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{studiengang_id}/lectures",
    response_model=list[dict[str, Any]],
    summary="Vorlesungen eines Studiengangs abrufen",
    response_description="Liste aller Vorlesungen für diesen Studiengang",
    responses={
        404: {"description": "Keine Vorlesungen für diesen Studiengang gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_studiengang_lectures(
    studiengang_id: str,
    semester: int | None = Query(None, description="Filtert nach Semesternummer (z. B. `3`)"),
) -> list[dict[str, Any]]:
    """Gibt alle Vorlesungen zurück, die einem bestimmten Studiengang zugeordnet sind."""
    try:
        db = mongo_client.get_db()
        query: dict[str, Any] = {"studiengang_id": studiengang_id}
        if semester is not None:
            query["$or"] = [{"semesterId": f"sem_{semester}"}, {"semester": semester}]

        lectures = serialize_docs(list(db.lectures.find(query)))

        if not lectures:
            raise HTTPException(status_code=404, detail="No lectures found for this Studiengang")

        return lectures

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lectures: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{studiengang_id}/timetable",
    response_model=dict[str, Any],
    summary="Kombinierten Stundenplan eines Studiengangs abrufen",
    response_description="Studiengang, gefilterte Vorlesungen, öffentliche Events und verfügbare Semester",
    responses={
        404: {"description": "Studiengang nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_studiengang_timetable(
    studiengang_id: str,
    semester: int | None = Query(None, description="Nach Semesternummer filtern (z. B. `3`)"),
    eventGroupId: str | None = Query(None, description="Events auf eine Gruppe beschränken (z. B. `sports`)"),
    limit_lectures: int = Query(200, ge=1, le=1000, description="Max. Vorlesungen"),
    limit_events: int = Query(50, ge=1, le=200, description="Max. Events"),
) -> dict[str, Any]:
    """Gibt Studiengang, zugehörige Vorlesungen und öffentliche Events gebündelt zurück.

    Praktisch für das Frontend: ein einziger Call liefert alles, was für die
    Stundenplan-Ansicht eines bestimmten Studiengangs nötig ist.
    """
    try:
        db = mongo_client.get_db()

        studiengang = db.studiengaenge.find_one({"_id": studiengang_id})
        if not studiengang:
            raise HTTPException(status_code=404, detail="Studiengang not found")

        # Vorlesungen: nach Studiengang, optional auch nach Semester
        lec_query: dict[str, Any] = {
            "$or": [
                {"studiengang_id": studiengang_id},
                {"courseOfStudyId": studiengang_id},
            ]
        }
        if semester is not None:
            lec_query = {"$and": [
                lec_query,
                {"$or": [{"semesterId": f"sem_{semester}"}, {"semester": semester}]},
            ]}

        raw_lectures = serialize_docs(
            list(db.lectures.find(lec_query).limit(limit_lectures))
        )

        # Distinct Semesternummern aus den gefundenen Vorlesungen ableiten
        semester_ids: list[str] = sorted({
            str(l.get("semesterId") or l.get("semester", ""))
            for l in raw_lectures
            if l.get("semesterId") or l.get("semester")
        })

        # Öffentliche Events (campusweit, nicht studiengang-spezifisch)
        evt_query: dict[str, Any] = {"is_public": True}
        if eventGroupId:
            evt_query["$or"] = [{"groupId": eventGroupId}, {"category": eventGroupId}]

        raw_events = serialize_docs(
            list(db.events.find(evt_query).limit(limit_events))
        )

        doc = _serialize_studiengang_document(studiengang)
        doc["related_courses"] = _related_courses(db, doc.get("program_code"), doc.get("code", ""))

        return {
            "studiengang": doc,
            "semesters": semester_ids,
            "lectures": raw_lectures,
            "events": raw_events,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timetable for Studiengang {studiengang_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
