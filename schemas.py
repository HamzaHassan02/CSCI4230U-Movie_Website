import re
from typing import Any, Dict

from marshmallow import Schema, ValidationError, fields, pre_load, validates, validate


class RegisterSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    role = fields.Str(load_default="user", validate=validate.OneOf(["admin", "user"]))

    @pre_load
    def strip_username(self, data: Dict[str, Any], **kwargs):
        username = data.get("username")
        if isinstance(username, str):
            data["username"] = username.strip()
        return data

    @validates("username")
    def validate_username(self, value: str, **kwargs):
        if len(value) < 4:
            raise ValidationError("Username must have at least 4 characters")
        if not re.fullmatch(r"[A-Za-z0-9_]+", value):
            raise ValidationError("Username may only contain letters, numbers, and underscores")

    @validates("password")
    def validate_password(self, value: str, **kwargs):
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters")
        if not re.search(r"\d", value):
            raise ValidationError("Password must have a number")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValidationError("Password must have at least 1 special character")


register_schema = RegisterSchema()
