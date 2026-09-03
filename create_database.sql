
-- =========================
-- PARAMS TABLE
-- =========================
CREATE TABLE Params (
    id SERIAL PRIMARY KEY,
    param_type VARCHAR(50) NOT NULL,
    param_value VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Active',
    description VARCHAR(255)
);

-- Species: Target animals
CREATE TABLE Species (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, 
    status VARCHAR(50) NOT NULL DEFAULT 'Active'
);

-- Trap Types: Specific models
CREATE TABLE Trap_Types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, 
    status VARCHAR(50) NOT NULL DEFAULT 'Active'
);

-- Trap Status: Current state (e.g., Sprung)
CREATE TABLE Trap_Status (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, 
    status VARCHAR(50) NOT NULL DEFAULT 'Active'
);

-- Bait Types: Used lures
CREATE TABLE Bait_Types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, 
    status VARCHAR(50) NOT NULL DEFAULT 'Active'
);

-- Bait Station Types: Used lures
CREATE TABLE Bait_Station_Types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, 
    status VARCHAR(50) NOT NULL DEFAULT 'Active'
);

-- =========================
-- USERS
-- =========================
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50),
    phone_number VARCHAR(20) NOT NULL,
    emergency_contact_name VARCHAR(100) NOT NULL,
    emergency_contact_phone_number VARCHAR(20) NOT NULL,
    emergency_contact_relationship VARCHAR(50) NOT NULL,
    is_super_admin BOOLEAN DEFAULT FALSE,
    account_status VARCHAR(100) NOT NULL
);

-- =========================
-- GROUPS
-- =========================
CREATE TABLE Groups (
    group_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    charitable_name VARCHAR(255),
    charity_registration_number VARCHAR(20),
    donation_description TEXT,
    image_url VARCHAR(255),
    is_public BOOLEAN DEFAULT TRUE,
    status VARCHAR(50) DEFAULT 'Pending', -- For Super Admin approval (Pending, Active, Rejected)
    operational_area JSONB,
    created_by INT NOT NULL REFERENCES Users(user_id)
);

-- =========================
-- GROUP MEMBERSHIP (Roles per Group)
-- =========================
CREATE TABLE Group_Members (
    id SERIAL PRIMARY KEY,
    group_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(50) NOT NULL, -- Group Coordinator, Operator, Observer
    membership_status VARCHAR(50) DEFAULT 'Active', -- Active, Pending, Inactive, Rejected
    FOREIGN KEY (group_id) REFERENCES Groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE(group_id, user_id)
);

-- =========================
-- LINE
-- =========================
CREATE TABLE Line (
    line_id SERIAL PRIMARY KEY,
    group_id INT NOT NULL,
    name VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL DEFAULT 'Trap',-- Trap, Bait
    line_status VARCHAR(50) NOT NULL DEFAULT 'Active',
    FOREIGN KEY (group_id) REFERENCES Groups(group_id) ON DELETE CASCADE
);
-- =========================
-- USER - LINE
-- =========================
CREATE TABLE User_Line (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    line_id INT NOT NULL,
    UNIQUE(user_id, line_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (line_id) REFERENCES Line(line_id)
);
-- =========================
-- TRAPS
-- =========================
CREATE TABLE Traps (
    trap_id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    trap_type_id INT NOT NULL,
    line_id INT NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    trap_status VARCHAR(50) NOT NULL DEFAULT 'Active',
    FOREIGN KEY (line_id) REFERENCES Line(line_id) ON DELETE CASCADE,
    FOREIGN KEY (trap_type_id) REFERENCES Trap_Types(id)

);
-- =========================
-- BAIT STATIONS
-- =========================
CREATE TABLE Bait_Stations (
    station_id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    line_id INT NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    bait_station_type_id INT NOT NULL,
    other_type_details TEXT, -- Used if "Other" is selected
    status VARCHAR(50) DEFAULT 'Active',
    FOREIGN KEY (line_id) REFERENCES Line(line_id) ON DELETE CASCADE,
    FOREIGN KEY (bait_station_type_id) REFERENCES Bait_Station_Types(id)
);
-- =========================
-- BAIT STATION RECORDS
-- =========================
CREATE TABLE Bait_Station_Records (
    record_id SERIAL PRIMARY KEY,
    station_id INT NOT NULL,
    recorded_by INT NOT NULL,
    date_recorded TIMESTAMP NOT NULL, -- ISO 8601 format
    target_species_id INT NOT NULL,
    active_ingredient VARCHAR(100) NOT NULL,
    formulation VARCHAR(200) NOT NULL,
    concentration NUMERIC(5,2) NOT NULL, -- Percentage
    bait_remaining NUMERIC(10,3) NOT NULL, -- In Kg
    bait_removed NUMERIC(10,3) DEFAULT 0,  -- In Kg
    bait_added NUMERIC(10,3) DEFAULT 0,    -- In Kg
    notes TEXT,
    FOREIGN KEY (station_id) REFERENCES Bait_Stations(station_id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by) REFERENCES Users(user_id),
    FOREIGN KEY (target_species_id) REFERENCES Species(id)
);

-- =========================
-- TRAP CATCH RECORDS
-- =========================
CREATE TABLE Trap_Catches (
    catch_id SERIAL PRIMARY KEY,
    trap_id INT NOT NULL,
    recorded_by INT,
    date TIMESTAMP NOT NULL,
    species_caught_id INT NOT NULL,
    sex VARCHAR(100) NOT NULL,
    maturity VARCHAR(100),
    trap_status_id INT NOT NULL,
    rebaited VARCHAR(100) NOT NULL,
    bait_type_id INT NOT NULL,
    trap_condition VARCHAR(100) NOT NULL,
    strikes INT NOT NULL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (trap_id) REFERENCES Traps(trap_id),
    FOREIGN KEY (recorded_by) REFERENCES Users(user_id),
    FOREIGN KEY (species_caught_id) REFERENCES Species(id),
    FOREIGN KEY (bait_type_id) REFERENCES Bait_Types(id),
    FOREIGN KEY (trap_status_id) REFERENCES Trap_Status(id)
);
-- =========================
-- OPERATOR NOTIFICATIONS
-- =========================
CREATE TABLE Notifications (
    notification_id SERIAL PRIMARY KEY,
    group_id INT,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES Groups(group_id) ON DELETE CASCADE
);


-- =========================
-- OBSERVATION TABLE
-- =========================
CREATE TABLE Observation (
    id SERIAL PRIMARY KEY,
    operator_id INT,
    line_id INT,
    date_recorded TIMESTAMP NOT NULL,
    notes TEXT,
    FOREIGN KEY (operator_id) REFERENCES Users(user_id),
    FOREIGN KEY (line_id) REFERENCES Line(line_id)
);
--***************************************************************************
-- The following tables are for the Group Updates and Knowledge Hub features.
--***************************************************************************
-- =========================
-- GROUP UPDATES
-- =========================
CREATE TABLE Group_Updates (
    update_id SERIAL PRIMARY KEY,
    group_id INT NOT NULL REFERENCES Groups(group_id) ON DELETE CASCADE,
    author_id INT NOT NULL REFERENCES Users(user_id),
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'Draft', -- Draft, Published
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- UPDATE ATTACHMENTS
-- =========================
CREATE TABLE Update_Attachments (
    attachment_id SERIAL PRIMARY KEY,
    update_id INT NOT NULL REFERENCES Group_Updates(update_id) ON DELETE CASCADE,
    file_url VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- e.g., 'image', 'pdf'
    description TEXT
);

-- =========================
-- UPDATE INTERACTIONS
-- =========================
CREATE TABLE Update_Comments (
    comment_id SERIAL PRIMARY KEY,
    update_id INT NOT NULL REFERENCES Group_Updates(update_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Update_Likes (
    id SERIAL PRIMARY KEY,
    update_id INT NOT NULL REFERENCES Group_Updates(update_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (update_id, user_id)
);
CREATE TABLE Comments_Likes (
    id SERIAL PRIMARY KEY,
    comment_id INT NOT NULL REFERENCES Update_Comments(comment_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    UNIQUE (comment_id, user_id)
);
CREATE TABLE Deleted_Comments_Log (
    log_id SERIAL PRIMARY KEY,
    original_comment_id INT,
    update_id INT NOT NULL,
    author_id INT NOT NULL,      -- Who wrote the bad comment
    moderator_id INT NOT NULL,   -- The Coordinator who deleted it
    content_snapshot TEXT,       -- The inappropriate text (for evidence)
    deletion_reason TEXT,        -- e.g., "Inappropriate language"
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (moderator_id) REFERENCES Users(user_id)
);
-- =========================
-- KNOWLEDGE HUB CATEGORIES
-- =========================
CREATE TABLE Knowledge_Categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL -- e.g., 'Trap Management', 'Bait Stations'
);

-- =========================
-- KNOWLEDGE ENTRIES
-- =========================
CREATE TABLE Knowledge_Entries (
    entry_id SERIAL PRIMARY KEY,
    category_id INT REFERENCES Knowledge_Categories(category_id) ON DELETE SET NULL,
    author_id INT REFERENCES Users(user_id),
    approved_by INT REFERENCES Users(user_id), -- The Group Coordinator who approved it
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    image_url VARCHAR(255),
    is_featured BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'Pending', -- Pending, Published, Archived
    version_number INT DEFAULT 1,
    parent_entry_id INT REFERENCES Knowledge_Entries(entry_id) ON DELETE SET NULL, -- For version history
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- GROUP THEMES (JSON Implementation)
-- =========================
CREATE TABLE Group_Themes (
    theme_id SERIAL PRIMARY KEY,
    group_id INT REFERENCES Groups(group_id) ON DELETE CASCADE, -- NULL = Pre-made Gallery theme
    theme_name VARCHAR(100) NOT NULL,
    settings JSONB NOT NULL, 
    is_active BOOLEAN DEFAULT FALSE,
    version_number INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT REFERENCES Users(user_id)
);

-- =========================
-- DONATIONS
-- =========================
CREATE TABLE Donations (
    donation_id SERIAL PRIMARY KEY,
    group_id INT REFERENCES Groups(group_id) ON DELETE SET NULL, -- NULL = Platform Support/General
    donor_id INT REFERENCES Users(user_id) ON DELETE SET NULL,     -- Optional logged-in user
    
    amount NUMERIC(10,2) NOT NULL,
    donation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    donation_type VARCHAR(50) NOT NULL, -- 'Group', 'Platform', 'General'
    
    -- Donor Info
    donor_name VARCHAR(255),               -- Required for tax receipt
    donor_email VARCHAR(255) NOT NULL,      -- For receipt delivery
    is_anonymous BOOLEAN DEFAULT FALSE,
    message TEXT,                          -- Optional supporter message
    
    -- Status for receipt generation
    receipt_issued BOOLEAN DEFAULT FALSE
);

-- =========================
-- USER POINTS (Progression)
-- =========================
CREATE TABLE User_Points (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES Users(user_id) ON DELETE CASCADE,
    cumulative_points INT DEFAULT 0,
    notes VARCHAR(255) NOT NULL, -- e.g., "Points from trap catches, bait station maintenance"
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- BADGE REDEMPTIONS (Physical Logistics)
-- =========================
CREATE TABLE Badge_Redemptions (
    redemption_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES Users(user_id),
    badge_name VARCHAR(50) NOT NULL, -- e.g., 'Kauri Kiwi'
    
    -- NZ Delivery Details
    recipient_name VARCHAR(100) NOT NULL,
    shipping_address TEXT NOT NULL,
    city VARCHAR(50) NOT NULL,
    postcode VARCHAR(10) NOT NULL,
    
    status VARCHAR(50) DEFAULT 'Pending', -- Pending, Shipped, Delivered
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    shipped_at TIMESTAMP,
    
    UNIQUE(user_id, badge_name) -- Prevents claiming the same physical badge twice
);
