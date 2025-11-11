from typing import List
from packages.config.settings import settings

def allowed_segments_for_role(role: str | None) -> List[int]:
    roles_map = settings.load_roles()
    # rol explícito
    if role and role in roles_map:
        return roles_map[role]
    # fallback al rol por defecto si existe
    if settings.DEFAULT_ROLE in roles_map:
        return roles_map[settings.DEFAULT_ROLE]
    return []
