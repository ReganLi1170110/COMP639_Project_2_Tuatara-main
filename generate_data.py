"""
Data Generator for Conservation Track Database
===============================================
Generates realistic fake data for all tables, in dependency order.
Predefined seed data (Params, Species, Trap_Types, etc. and the 10 existing
users/groups/lines) are never re-inserted – only new rows are added.

Usage
-----
  python generate_data.py                     # use all defaults
  python generate_data.py --groups 5          # generate 5 extra groups
  python generate_data.py --help              # show all options

All counts control how many *new* rows are inserted on top of existing data.
"""

import argparse
import random
import string
import sys
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
from app.db import connect

# ---------------------------------------------------------------------------
# ── Database connection (mirrors connect.py) ────────────────────────────────
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "host": connect.dbhost,
    "port": connect.dbport,
    "dbname": connect.dbname,
    "user": connect.dbuser,
    "password": connect.dbpass,
}

# ---------------------------------------------------------------------------
# ── CLI arguments ────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="Generate fake data for the Conservation Track database."
    )
    p.add_argument("--groups",           type=int, default=10,  help="Extra groups to create (default 10)")
    p.add_argument("--users-per-group",  type=int, default=5,  help="New users per generated group (default 5)")
    p.add_argument("--lines-per-group",  type=int, default=15,  help="Lines per generated group (default 20)")
    p.add_argument("--traps-per-line",   type=int, default=14,  help="Traps per Trap line (default 14)")
    p.add_argument("--stations-per-line",type=int, default=14,  help="Bait stations per Bait line (default 4)")
    p.add_argument("--catches-per-trap", type=int, default=5,  help="Trap catch records per trap (default 5)")
    p.add_argument("--records-per-station", type=int, default=5, help="Bait station records per station (default 3)")
    p.add_argument("--observations",     type=int, default=5, help="Extra observations to create (default 20)")
    p.add_argument("--updates-per-group",type=int, default=13,  help="Group updates per generated group (default 13)")
    p.add_argument("--donations",        type=int, default=10, help="Extra donations to create (default 10)")
    p.add_argument("--knowledge",        type=int, default=10,  help="Extra knowledge entries (default 10)")
    p.add_argument("--points",           type=int, default=20,  help="Upsert point records for new users (default 20)")
    p.add_argument("--seed",             type=int, default=None, help="Random seed for reproducibility")
    return p.parse_args()

# ---------------------------------------------------------------------------
# ── Helpers ──────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------
def rand_str(n=8):
    return "".join(random.choices(string.ascii_lowercase, k=n))

def rand_nz_phone():
    return "021" + "".join(random.choices(string.digits, k=7))

def rand_date(start_year=2023, end_year=2026):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 6, 1)
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def rand_nz_lat():
    return round(random.uniform(-47.0, -34.5), 6)

def rand_nz_lon():
    return round(random.uniform(166.5, 178.5), 6)

def fetch_all_ids(cur, table, id_col):
    cur.execute(f"SELECT {id_col} FROM {table}")
    return [r[id_col] for r in cur.fetchall()]

def fetch_all_ids_where(cur, table, id_col, where_col, where_val):
    cur.execute(
        f"SELECT {id_col} FROM {table} WHERE {where_col} = %s",
        (where_val,)
    )
    return [r[id_col] for r in cur.fetchall()]

NZ_REGIONS = [
    "Northland", "Auckland", "Waikato", "Bay of Plenty", "Gisborne",
    "Hawke's Bay", "Taranaki", "Manawatū-Whanganui", "Wellington",
    "Tasman", "Nelson", "Marlborough", "West Coast", "Canterbury",
    "Otago", "Southland",
]

GROUP_ADJECTIVES = [
    "Green", "Wild", "Forest", "River", "Coastal", "Mountain", "Valley",
    "Highland", "Bush", "Native", "Wetland", "Tussock", "Alpine",
]
GROUP_NOUNS = [
    "Guardians", "Protectors", "Alliance", "Trust", "Society", "Watch",
    "Rangers", "Network", "Community", "Initiative",
]

FIRST_NAMES = [
    "Aroha", "James", "Mei", "Oliver", "Sophie", "Ethan", "Emily", "Noah",
    "Charlotte", "Liam", "Isabella", "Mason", "Mia", "Lucas", "Amelia",
    "Aiden", "Ella", "Jackson", "Avery", "Logan",
]
LAST_NAMES = [
    "Smith", "Jones", "Brown", "Taylor", "Williams", "Wilson", "Davies",
    "Thomas", "Evans", "Roberts", "Walker", "White", "Thompson", "Moore",
    "Martin", "Jackson", "Lee", "Harris", "Clark", "Lewis",
]

UPDATE_TITLES = [
    "Monthly Catch Report", "Volunteer Day Summary", "New Equipment Arrived",
    "Line Inspection Complete", "Bait Refresh Done", "Predator Alert",
    "Funding Announcement", "New Volunteer Welcome", "Training Session Recap",
    "Equipment Maintenance", "Quarterly Review", "Seasonal Reset",
]

KNOWLEDGE_TITLES = [
    "Best Practices for Trap Placement", "Identifying Predator Sign",
    "Bait Selection Guide", "Seasonal Pest Activity", "GPS Mapping Tips",
    "Safe Chemical Handling", "Night Trapping Safety", "Record Keeping Guide",
    "Volunteer Briefing Template", "Emergency Field Protocol",
]

DONATION_MESSAGES = [
    "Keep up the great work!", "Happy to support this cause.",
    "For the birds!", "Go team!", None, None,
]

# ---------------------------------------------------------------------------
# ── Main generator ───────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------
def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    conn = psycopg2.connect(cursor_factory=psycopg2.extras.RealDictCursor, **DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    try:
        print("=== Conservation Track Data Generator ===\n")

        # ── Load lookup tables ───────────────────────────────────────────────
        print("Loading reference data...")
        species_ids       = fetch_all_ids(cur, "Species",           "id")
        trap_type_ids     = fetch_all_ids(cur, "Trap_Types",        "id")
        trap_status_ids   = fetch_all_ids(cur, "Trap_Status",       "id")
        bait_type_ids     = fetch_all_ids(cur, "Bait_Types",        "id")
        bst_ids           = fetch_all_ids(cur, "Bait_Station_Types","id")
        kcat_ids          = fetch_all_ids(cur, "Knowledge_Categories","category_id")

        active_ingredients = [
            "Brodifacoum", "Diphacinone", "Pindone",
            "Cholecalciferol", "Coumateralyl", "PAPP", "Bromadiolone",
        ]
        formulations = ["Pellet", "Cereal", "Paste", "Block", "Gel"]
        sexes        = ["Male", "Female"]
        maturities   = ["Juvenile", "Adult"]
        rebaited_opts = ["Yes", "No"]
        conditions    = ["OK", "Needs maintenance", "Repaired", "Regassed", "Battery charge"]
        member_roles  = ["Operator", "Observer"]

        # ── Existing coordinator IDs ─────────────────────────────────────────
        cur.execute("SELECT user_id FROM Users WHERE is_super_admin = FALSE ORDER BY user_id LIMIT 3")
        existing_coords = [r["user_id"] for r in cur.fetchall()]
        super_admin_id  = 1   # always user_id 1

        # ── Track generated objects ──────────────────────────────────────────
        new_group_ids    = []
        new_coord_ids    = []   # coordinator per new group
        new_user_ids     = []   # non-coordinator users in new groups
        new_trap_line_ids = []
        new_bait_line_ids = []
        new_trap_ids     = []
        new_station_ids  = []

        # ── Generate Groups ──────────────────────────────────────────────────
        if args.groups > 0:
            print(f"\n[Groups] Creating {args.groups} groups...")
            cur.execute("SELECT name FROM Groups")
            existing_names = {r["name"] for r in cur.fetchall()}
            used_names = set(existing_names)

            for i in range(args.groups):
                # Create a coordinator user for this group
                fn  = random.choice(FIRST_NAMES)
                ln  = random.choice(LAST_NAMES)
                uname = f"coord_{rand_str(6)}"
                email = f"{uname}@generated.nz"
                # bcrypt hash of "Password1!" — safe constant for test data
                pw_hash = "$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW"
                cur.execute(
                    """INSERT INTO Users
                       (username, email, password_hash, first_name, last_name,
                        phone_number, emergency_contact_name,
                        emergency_contact_phone_number, emergency_contact_relationship,
                        is_super_admin, account_status)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE,'Active')
                       RETURNING user_id""",
                    (uname, email, pw_hash, fn, ln, rand_nz_phone(),
                     random.choice(FIRST_NAMES), rand_nz_phone(), "Friend")
                )
                coord_id = cur.fetchone()["user_id"]
                new_coord_ids.append(coord_id)

                # Create the group
                region = random.choice(NZ_REGIONS)
                for attempt in range(20):
                    g_name = f"{region} {random.choice(GROUP_ADJECTIVES)} {random.choice(GROUP_NOUNS)}"
                    if g_name not in used_names:
                        break
                else:
                    g_name = f"Group {rand_str(8)}"
                used_names.add(g_name)
                is_public = random.choice([True, True, False])
                reg_num   = f"CC{random.randint(10000,99999)}" if random.random() > 0.4 else None
                char_name = f"{g_name} Trust" if reg_num else None
                cur.execute(
                    """INSERT INTO Groups
                       (name, description, charitable_name, charity_registration_number,
                        is_public, status, created_by)
                       VALUES (%s,%s,%s,%s,%s,'Active',%s)
                       RETURNING group_id""",
                    (g_name,
                     f"Predator control in the {region} region.",
                     char_name, reg_num, is_public, coord_id)
                )
                gid = cur.fetchone()["group_id"]
                new_group_ids.append(gid)

                # Add coordinator as Group Coordinator
                cur.execute(
                    """INSERT INTO Group_Members (group_id, user_id, role, membership_status)
                       VALUES (%s,%s,'Coordinator','Active')
                       ON CONFLICT (group_id, user_id) DO NOTHING""",
                    (gid, coord_id)
                )

                # Add regular members
                for _ in range(args.users_per_group):
                    fn2  = random.choice(FIRST_NAMES)
                    ln2  = random.choice(LAST_NAMES)
                    u2   = f"user_{rand_str(7)}"
                    em2  = f"{u2}@generated.nz"
                    role2 = random.choice(member_roles)
                    cur.execute(
                        """INSERT INTO Users
                           (username, email, password_hash, first_name, last_name,
                            phone_number, emergency_contact_name,
                            emergency_contact_phone_number, emergency_contact_relationship,
                            is_super_admin, account_status)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE,'Active')
                           RETURNING user_id""",
                        (u2, em2, pw_hash, fn2, ln2, rand_nz_phone(),
                         random.choice(FIRST_NAMES), rand_nz_phone(), "Partner")
                    )
                    uid2 = cur.fetchone()["user_id"]
                    new_user_ids.append(uid2)
                    cur.execute(
                        """INSERT INTO Group_Members (group_id, user_id, role, membership_status)
                           VALUES (%s,%s,%s,'Active')
                           ON CONFLICT (group_id, user_id) DO NOTHING""",
                        (gid, uid2, role2)
                    )

                print(f"  Group '{g_name}' (id={gid}) + {args.users_per_group+1} users")

        # ── Reload all group/user IDs (includes existing + new) ─────────────
        all_group_ids = fetch_all_ids(cur, "Groups", "group_id")
        all_user_ids  = fetch_all_ids(cur, "Users",  "user_id")

        # ── Generate Lines ───────────────────────────────────────────────────
        if new_group_ids and args.lines_per_group > 0:
            print(f"\n[Lines] Creating up to {args.lines_per_group} lines per new group...")
            cur.execute("SELECT name FROM Line")
            used_line_names = {r["name"] for r in cur.fetchall()}

            for gid in new_group_ids:
                cur.execute("SELECT name FROM Groups WHERE group_id = %s", (gid,))
                prefix = "".join(w[0] for w in cur.fetchone()["name"].split()[:2]).upper()
                for j in range(args.lines_per_group):
                    ltype   = "Trap" if j % 2 == 0 else "Bait"
                    suffix  = f"T{j+1}" if ltype == "Trap" else f"B{j+1}"
                    l_name  = f"{prefix}-{suffix}"
                    # Guarantee uniqueness
                    attempt = 0
                    while l_name in used_line_names:
                        attempt += 1
                        l_name = f"{prefix}-{suffix}-{attempt}"
                    used_line_names.add(l_name)
                    cur.execute(
                        """INSERT INTO Line (group_id, name, type, line_status)
                           VALUES (%s,%s,%s,'Active') RETURNING line_id""",
                        (gid, l_name, ltype)
                    )
                    lid = cur.fetchone()["line_id"]
                    if ltype == "Trap":
                        new_trap_line_ids.append(lid)
                    else:
                        new_bait_line_ids.append(lid)

                    # Assign operators in this group to the new line
                    cur.execute(
                        """SELECT user_id FROM Group_Members
                           WHERE group_id = %s AND role = 'Operator'""",
                        (gid,)
                    )
                    ops = [r["user_id"] for r in cur.fetchall()]
                    for op in ops[:2]:   # assign up to 2 operators per line
                        cur.execute(
                            """INSERT INTO User_Line (user_id, line_id)
                               VALUES (%s,%s) ON CONFLICT (user_id, line_id) DO NOTHING""",
                            (op, lid)
                        )
                    print(f"  Line '{l_name}' ({ltype}, id={lid}) → group {gid}")

        # ── Generate Traps ───────────────────────────────────────────────────
        all_trap_line_ids = fetch_all_ids_where(cur, "Line", "line_id", "type", "Trap")
        target_trap_lines = new_trap_line_ids if new_trap_line_ids else []

        if target_trap_lines and args.traps_per_line > 0:
            print(f"\n[Traps] Creating {args.traps_per_line} traps per new trap line...")
            cur.execute("SELECT code FROM Traps")
            used_codes = {r["code"] for r in cur.fetchall()}
            for lid in target_trap_lines:
                for k in range(args.traps_per_line):
                    code = None
                    for _ in range(50):
                        c = "T" + "".join(random.choices(string.digits, k=4))
                        if c not in used_codes:
                            code = c
                            used_codes.add(c)
                            break
                    if code is None:
                        code = f"T{rand_str(5)}"
                    cur.execute(
                        """INSERT INTO Traps
                           (code, trap_type_id, line_id, latitude, longitude, trap_status)
                           VALUES (%s,%s,%s,%s,%s,'Active') RETURNING trap_id""",
                        (code, random.choice(trap_type_ids), lid,
                         rand_nz_lat(), rand_nz_lon())
                    )
                    new_trap_ids.append(cur.fetchone()["trap_id"])
            print(f"  Created {len(new_trap_ids)} traps")

        # ── Generate Bait Stations ───────────────────────────────────────────
        target_bait_lines = new_bait_line_ids if new_bait_line_ids else []

        if target_bait_lines and args.stations_per_line > 0:
            print(f"\n[Bait Stations] Creating {args.stations_per_line} stations per new bait line...")
            cur.execute("SELECT code FROM Bait_Stations")
            used_bs_codes = {r["code"] for r in cur.fetchall()}
            for lid in target_bait_lines:
                for k in range(args.stations_per_line):
                    code = None
                    for _ in range(50):
                        c = "B" + "".join(random.choices(string.digits, k=4))
                        if c not in used_bs_codes:
                            code = c
                            used_bs_codes.add(c)
                            break
                    if code is None:
                        code = f"B{rand_str(5)}"
                    cur.execute(
                        """INSERT INTO Bait_Stations
                           (code, line_id, latitude, longitude, bait_station_type_id, status)
                           VALUES (%s,%s,%s,%s,%s,'Active') RETURNING station_id""",
                        (code, lid, rand_nz_lat(), rand_nz_lon(),
                         random.choice(bst_ids))
                    )
                    new_station_ids.append(cur.fetchone()["station_id"])
            print(f"  Created {len(new_station_ids)} bait stations")

        # ── Generate Trap Catches ────────────────────────────────────────────
        if new_trap_ids and args.catches_per_trap > 0:
            print(f"\n[Trap Catches] Creating {args.catches_per_trap} catches per new trap...")
            # Gather operators (anyone who can record catches)
            cur.execute("SELECT user_id FROM Users WHERE is_super_admin = FALSE")
            recorder_ids = [r["user_id"] for r in cur.fetchall()]
            count = 0
            for tid in new_trap_ids:
                for _ in range(args.catches_per_trap):
                    cur.execute(
                        """INSERT INTO Trap_Catches
                           (trap_id, recorded_by, date, species_caught_id, sex, maturity,
                            trap_status_id, rebaited, bait_type_id, trap_condition, strikes, notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (tid,
                         random.choice(recorder_ids),
                         rand_date(),
                         random.choice(species_ids),
                         random.choice(sexes),
                         random.choice(maturities + [None]),
                         random.choice(trap_status_ids),
                         random.choice(rebaited_opts),
                         random.choice(bait_type_ids),
                         random.choice(conditions),
                         random.randint(0, 5),
                         f"Auto-generated catch record." if random.random() > 0.6 else None)
                    )
                    count += 1
            print(f"  Created {count} trap catch records")

        # ── Generate Bait Station Records ────────────────────────────────────
        if new_station_ids and args.records_per_station > 0:
            print(f"\n[Bait Station Records] Creating {args.records_per_station} records per new station...")
            cur.execute("SELECT user_id FROM Users WHERE is_super_admin = FALSE")
            recorder_ids = [r["user_id"] for r in cur.fetchall()]
            count = 0
            for sid in new_station_ids:
                for _ in range(args.records_per_station):
                    remaining = round(random.uniform(0, 1), 3)
                    added     = round(random.uniform(0, 1 - remaining), 3)
                    removed   = round(random.uniform(0, remaining), 3)
                    cur.execute(
                        """INSERT INTO Bait_Station_Records
                           (station_id, recorded_by, date_recorded, target_species_id,
                            active_ingredient, formulation, concentration,
                            bait_remaining, bait_removed, bait_added, notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (sid,
                         random.choice(recorder_ids),
                         rand_date(),
                         random.choice(species_ids),
                         random.choice(active_ingredients),
                         random.choice(formulations),
                         round(random.choice([0.05, 0.10, 0.02]), 2),
                         remaining, removed, added,
                         "Auto-generated record." if random.random() > 0.6 else None)
                    )
                    count += 1
            print(f"  Created {count} bait station records")

        # ── Generate Observations ────────────────────────────────────────────
        if args.observations > 0:
            print(f"\n[Observations] Creating {args.observations} observations...")
            all_line_ids = fetch_all_ids(cur, "Line", "line_id")
            cur.execute("SELECT user_id FROM Users WHERE is_super_admin = FALSE")
            non_admin_ids = [r["user_id"] for r in cur.fetchall()]
            for line_id in all_line_ids:
                for _ in range(args.observations):
                    cur.execute(
                        """INSERT INTO Observation (operator_id, line_id, date_recorded, notes)
                        VALUES (%s,%s,%s,%s)""",
                        (random.choice(non_admin_ids),
                        line_id,
                        rand_date(),
                        f"Observed sign of predator activity. Auto-generated.")
                    )
            print(f"  Created {args.observations} observations")

        # ── Generate Group Updates ───────────────────────────────────────────
        if new_group_ids and args.updates_per_group > 0:
            print(f"\n[Group Updates] Creating {args.updates_per_group} updates per new group...")
            count = 0
            for gid in new_group_ids:
                # Author = coordinator of the group
                cur.execute(
                    "SELECT user_id FROM Group_Members WHERE group_id = %s AND role = 'Coordinator' LIMIT 1",
                    (gid,)
                )
                row = cur.fetchone()
                author_id = row["user_id"] if row else super_admin_id
                for _ in range(args.updates_per_group):
                    title   = random.choice(UPDATE_TITLES)
                    content = f"Auto-generated update for group {gid}. {rand_str(20)}"
                    cur.execute(
                        """INSERT INTO Group_Updates
                           (group_id, author_id, title, content, status)
                           VALUES (%s,%s,%s,%s,'Published')""",
                        (gid, author_id, title, content)
                    )
                    count += 1
            print(f"  Created {count} group updates")

        # ── Generate Donations ───────────────────────────────────────────────
        if args.donations > 0:
            print(f"\n[Donations] Creating {args.donations} donations...")
            donation_types = ["Group Donation", "Platform Support", "General Support"]
            all_grp_ids = fetch_all_ids(cur, "Groups", "group_id")
            for _ in range(args.donations):
                dtype = random.choice(donation_types)
                gid   = random.choice(all_grp_ids) if dtype == "Group Donation" else None
                donor = random.choice(FIRST_NAMES) + " " + random.choice(LAST_NAMES)
                email = f"donor_{rand_str(6)}@test.nz"
                anon  = random.random() < 0.25
                cur.execute(
                    """INSERT INTO Donations
                       (group_id, amount, donation_date, donation_type,
                        donor_name, donor_email, is_anonymous, message)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (gid,
                     round(random.uniform(5, 500), 2),
                     rand_date(),
                     dtype,
                     donor, email, anon,
                     random.choice(DONATION_MESSAGES))
                )
            print(f"  Created {args.donations} donations")

        # ── Generate Knowledge Entries ───────────────────────────────────────
        if args.knowledge > 0 and kcat_ids:
            print(f"\n[Knowledge] Creating {args.knowledge} knowledge entries...")
            cur.execute("SELECT user_id FROM Users WHERE is_super_admin = FALSE ORDER BY user_id LIMIT 5")
            author_ids = [r["user_id"] for r in cur.fetchall()]
            for _ in range(args.knowledge):
                title   = random.choice(KNOWLEDGE_TITLES) + " – " + rand_str(5)
                content = f"Auto-generated knowledge article. {rand_str(40)}"
                cur.execute(
                    """INSERT INTO Knowledge_Entries
                       (category_id, author_id, approved_by, title, content, status)
                       VALUES (%s,%s,%s,%s,%s,'Published')""",
                    (random.choice(kcat_ids),
                     random.choice(author_ids),
                     super_admin_id,
                     title, content)
                )
            print(f"  Created {args.knowledge} knowledge entries")

        # ── Generate User Points ─────────────────────────────────────────────
        all_new_users = new_coord_ids + new_user_ids
        if all_new_users:
            print(f"\n[User Points] Creating point records for {len(all_new_users)} new users...")
            for uid in all_new_users:
                pts = random.randint(0, 20)
                cur.execute(
                    """INSERT INTO User_Points (user_id, cumulative_points, notes)
                       VALUES (%s,%s,%s)
                       """,
                    (uid, pts, "Auto-generated points record.")
                    
                )
            print(f"  Done")

        # ── Generate Notifications ───────────────────────────────────────────
        if all_new_users:
            print(f"\n[Notifications] Creating welcome notifications for new users...")
            for uid in all_new_users:
                cur.execute(
                    """INSERT INTO Notifications (user_id, message, is_read)
                       VALUES (%s,%s,FALSE)""",
                    (uid, "Welcome to Conservation Track! Your account is ready.")
                )
            print(f"  Created {len(all_new_users)} notifications")

        conn.commit()
        print("\n✓ All data committed successfully.\n")

    except Exception as exc:
        conn.rollback()
        print(f"\n✗ Error – rolled back changes.\n{exc}", file=sys.stderr)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
