from __future__ import annotations


type JsonObject = dict[str, JsonValue]

type JsonValue = str | int | float | list[JsonValue] | JsonObject | None
