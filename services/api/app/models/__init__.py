"""Models package — import all models so Alembic sees them."""

from app.models.base import Base  # noqa: F401
from app.models.identity import Identity  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.academic_term import AcademicTerm  # noqa: F401
from app.models.campus import Campus  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.course import Course  # noqa: F401
from app.models.cohort import Cohort  # noqa: F401
from app.models.batch import Batch  # noqa: F401
from app.models.room import Room  # noqa: F401
from app.models.staff_profile import StaffProfile  # noqa: F401
from app.models.staff_availability_block import StaffAvailabilityBlock  # noqa: F401
from app.models.eligibility import Eligibility  # noqa: F401
from app.models.period_template import PeriodTemplate  # noqa: F401
from app.models.constraint_rule import ConstraintRule  # noqa: F401
from app.models.timetable_version import TimetableVersion  # noqa: F401
from app.models.assignment import Assignment  # noqa: F401
from app.models.student_profile import StudentProfile  # noqa: F401
from app.models.elective_section import ElectiveSection  # noqa: F401
from app.models.enrollment_record import EnrollmentRecord  # noqa: F401
from app.models.batch_membership import BatchMembership  # noqa: F401
from app.models.exam_timetable_version import ExamTimetableVersion  # noqa: F401
from app.models.exam_session import ExamSession  # noqa: F401
from app.models.stubs import (  # noqa: F401
    ExceptionCalendar,
    SubstitutionLog,
    AuditLog,
    Notification,
)
