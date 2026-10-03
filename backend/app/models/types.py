from sqlalchemy import Enum as SAEnum


def enum_type(enum_cls, name: str, length: int = 32) -> SAEnum:
    """Portable, validated enum stored as VARCHAR (no native PG enum => easy migrations)."""
    return SAEnum(enum_cls, name=name, native_enum=False, length=length, validate_strings=True)
