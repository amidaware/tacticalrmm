from enum import Enum


class MeshAgentIdent(Enum):
    WIN32 = 3
    WIN64 = 4
    LINUX32 = 5
    LINUX64 = 6
    LINUX_ARM_64 = 26
    LINUX_ARM_HF = 25

    def __str__(self):
        return str(self.value)


AGENT_DEFER = ("wmi_detail", "services")


WEEK_DAYS = {
    "Sunday": 0x1,
    "Monday": 0x2,
    "Tuesday": 0x4,
    "Wednesday": 0x8,
    "Thursday": 0x10,
    "Friday": 0x20,
    "Saturday": 0x40,
}

MONTHS = {
    "January": 0x1,
    "February": 0x2,
    "March": 0x4,
    "April": 0x8,
    "May": 0x10,
    "June": 0x20,
    "July": 0x40,
    "August": 0x80,
    "September": 0x100,
    "October": 0x200,
    "November": 0x400,
    "December": 0x800,
}

WEEKS = {
    "First Week": 0x1,
    "Second Week": 0x2,
    "Third Week": 0x4,
    "Fourth Week": 0x8,
    "Last Week": 0x10,
}

MONTH_DAYS = {f"{b}": 0x1 << a for a, b in enumerate(range(1, 32))}
MONTH_DAYS["Last Day"] = 0x80000000
