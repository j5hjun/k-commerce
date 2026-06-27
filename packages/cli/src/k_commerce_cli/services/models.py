from dataclasses import dataclass


@dataclass(frozen=True)
class Credentials:
    email: str
    password: str
