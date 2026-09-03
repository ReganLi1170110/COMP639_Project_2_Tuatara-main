# Facade Repository (Legacy Wrapper)
# This module acts as a centralized compatibility layer, delegating calls to the new modular 
# repository system (line_repository, trap_repository, catch_repository, etc.).
# It ensures existing route handlers continue to function without modifying their imports.

from app.repository.line_repository import (
    get_lines_with_assigned_users,
    get_lines_with_assigned_users_paginated,
    get_line_detail,
    create_line,
    update_line,
    retire_line,
    get_line_management_options,
    get_lines_by_group_organized_by_type
)
from app.repository.trap_repository import (
    get_traps_by_line,
    get_trap_types,
    add_trap_to_line,
    update_trap,
    retire_trap,
    deactivate_traps_by_line,
    trap_code_exists_exact
)
from app.repository.catch_repository import (
    get_trap_catches,
    get_all_catches,
    get_all_catches_paginated,
    get_catch_by_id,
    update_catch,
    get_trap_catches_summary_data,
    get_chart_operators
)
from app.repository.observation_repository import (
    get_observations_by_line,
    create_observation,
    update_observation,
    get_observation_by_id
)
from app.repository.user_repository import (
    get_users_with_assigned_lines_paginated,
    get_user_profile
)
from app.repository.dashboard_repository import (
    get_observer_dashboard_data,
    get_operator_dashboard_data,
    get_admin_dashboard_data
)
from app.repository.operator_repository import (
    get_unassigned_operators_for_line,
    assign_operator_to_line,
    remove_operator_from_line,
    replace_line_operator_assignments,
    get_operator_assigned_lines,
    handle_operator_assignment_with_notifications
)
from app.repository.common_repository import (
    get_manageable_param_types,
    get_manageable_param_types_with_counts,
    get_params_by_type,
    get_params_by_type_paginated,
    add_param,
    delete_param,
    is_param_value_in_use,
    get_params_by_type_with_id
)
from app.repository.notification_repository import (
    get_dashboard_notifications,
    create_line_assignment_notifications
)
from app.utils import get_cursor

# Compatibility aliases (if needed)
add_observation = create_observation
get_distinct_species = lambda: [{"species_caught": s['name'], "species_id": s['id']} for s in get_trap_types()] # This is slightly wrong but placeholder
# Actually I'll re-implement the small ones if they are too different.

def get_distinct_species():
    from app.repository.common_repository import get_species
    return [{"species_caught": s['name'], "species_id": s['id']} for s in get_species()]

def get_distinct_statuses():
    from app.repository.common_repository import get_trap_status
    return [{"status": s['name'], "status_id": s['id']} for s in get_trap_status()]

def get_distinct_trap_types():
    from app.repository.trap_repository import get_trap_types
    return [{"name": t['name'], "id": t['id']} for t in get_trap_types()]

# Compatibility aliases for modularized functions
get_operator_dashboard_notifications = get_dashboard_notifications
notify_line_assignment_change = create_line_assignment_notifications
handle_operator_assignment_with_mode = handle_operator_assignment_with_notifications

def add_param_value(param_type, param_value):
    from app.repository.common_repository import add_param
    return add_param(param_type, param_value)

def update_param_value(param_type, old_value, new_value):
    from app.repository.common_repository import get_params_by_type_with_id
    params = get_params_by_type_with_id(param_type)
    for p in params:
        if p['param_value'].lower().strip() == new_value.lower().strip() and p['param_value'] != old_value:
            raise ValueError("duplicate_param_value")
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE Params SET param_value = %s WHERE param_type = %s AND param_value = %s",
            (new_value, param_type, old_value)
        )

def delete_param_value(param_type, param_id):
    from app.repository.common_repository import is_param_value_in_use, delete_param
    if is_param_value_in_use(param_type, param_id):
        raise ValueError("param_value_in_use")
    return delete_param(param_id)
