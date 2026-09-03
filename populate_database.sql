-- Roles
INSERT INTO Params (param_type,param_value) VALUES
('user_role','Observer'),
('user_role','Operator'),
('user_role','Coordinator');
INSERT INTO Params (param_type,param_value) VALUES
('account_status','Active'),
('account_status','Inactive');
INSERT INTO Params (param_type,param_value) VALUES
('member_status','Pending'),
('member_status','Rejected'),
('member_status','Active'),
('member_status','Inactive');
-- Line Status
INSERT INTO Params (param_type,param_value) VALUES
('line_status','Pending'),
('line_status','Active'),
('line_status','Inactive');

-- Line Types
INSERT INTO Params (param_type,param_value) VALUES
('line_type','Trap'),
('line_type','Bait');



-- Sex
INSERT INTO Params (param_type,param_value) VALUES
('sex','Male'),
('sex','Female');

--active ingredient
INSERT INTO Params (param_type,param_value) VALUES
('active_ingredient','Brodifacoum'),
('active_ingredient','Diphacinone'),
('active_ingredient','Pindone'),
('active_ingredient','Cholecalciferol'),
('active_ingredient','Coumateralyl'),
('active_ingredient','PAPP'),
('active_ingredient','Bromadiolone');



-- Maturity
INSERT INTO Params (param_type,param_value) VALUES
('maturity','Juvenile'),
('maturity','Adult');

-- Trap Status2 for Traps
INSERT INTO Params (param_type,param_value) VALUES
('general_status','Active'),
('general_status','Inactive');

-- Rebaited
INSERT INTO Params (param_type,param_value) VALUES
('rebaited','Yes'),
('rebaited','No');

-- Trap Condition
INSERT INTO Params (param_type,param_value) VALUES
('trap_condition','OK'),
('trap_condition','Needs maintenance'),
('trap_condition','Repaired'),
('trap_condition','Regassed'),
('trap_condition','Recurred'),
('trap_condition','Battery charge');

-- Group Status (For Super Admin Approval Flow)
INSERT INTO Params (param_type, param_value) VALUES
('group_status', 'Pending'),
('group_status', 'Active'),
('group_status', 'Rejected'),
('group_status', 'Archived');
-- Redemptions Status
INSERT INTO Params (param_type, param_value) VALUES
('redemptions_status', 'Pending'),
('redemptions_status', 'Shipped'),
('redemptions_status', 'Delivered');
-- Donation Types
INSERT INTO Params (param_type, param_value) VALUES
('donation_type', 'Group Donation'),
('donation_type', 'Platform Support'),
('donation_type', 'General Support');
-- Update Status
INSERT INTO Params (param_type, param_value) VALUES
('update_status', 'Draft'),
('update_status', 'Published');

-- Knowledge Hub Status
INSERT INTO Params (param_type, param_value) VALUES
('knowledge_status', 'Pending'),
('knowledge_status', 'Published'),
('knowledge_status', 'Archived');

-- Update Status
INSERT INTO Params (param_type, param_value) VALUES
('update_status', 'Draft'),
('update_status', 'Published'),
('update_status', 'Archived');

-- Trap Types
INSERT INTO Trap_Types (name) VALUES
('A24'),
('DOC 150'),
('DOC 200'),
('DOC 250'),
('Flipping Timmy'),
('Rat trap'),
('T-Rex Rat Trap'),
('Trapinator'),
('Victor');

-- Species
INSERT INTO Species (name) VALUES
('Ferret'),
('Hedgehog'),
('Mouse'),
('Possum'),
('Kiore Rat'),
('Norway Rat'),
('Ship Rat'),
('Stoat'),
('Weasel'),
('Unspecified'),
('None');
-- trap catch status
INSERT INTO Trap_Status (name) VALUES
('Initial set'),
('Removed for Repair'),
('Sprung'),
('Still set, bait OK'),
('Still set, bait bad'),
('Still set, bait missing'),
('Trap Replaced'),
('Trap gone'),
('Trap interfered with');
-- Bait Types (Explicitly required by your brief)
INSERT INTO Bait_Types (name) VALUES
('Carrot'),
('Cereal'),
('Cheese'),
('Chocolate'),
('Dehydrated Rabbit'),
('Dried fruit'),
('Ferret bedding'),
('Fish'),
('Fresh Possum'),
('Fresh Rabbit'),
('Fresh fruit'),
('Fresh meat'),
('Golf ball'),
('Good Nature Chocolate'),
('Good Nature Meat Lovers'),
('Goodnature Blood'),
('Goodnature Cinnamon pre feed'),
('Goodnature Nut Butter'),
('Lure'),
('Lure-it Salmon Spray'),
('Mayo'),
('Mustelid and Cat Lure'),
('NARA Blocks'),
('NZAT Lure - Original'),
('None'),
('Nut'),
('Nutella'),
('Other'),
('Peanut butter'),
('PoaUku'),
('Possum Dough'),
('Rabbit oil'),
('Rat and Possum Lure'),
('Rat oil'),
('Salmon'),
('Salmon oil'),
('Salted Possum'),
('Salted Rabbit'),
('Salted meat'),
('Smooth'),
('Terracotta Lures'),
('Tinned Sardines'),
('Whole egg');

--Bait Station Types (Explicitly required by your brief)
INSERT INTO Bait_Station_Types (name) VALUES
('Bait Safe'),
('Chimney'),
('EnviroMate100'),
('Flowerpot'),
('Hockey stick'),
('KK'),
('Kilmore'),
('Mini Philproof'),
('PelGar Rat Station'),
('Philproof'),
('Pied Piper'),
('Protecta Ambush'),
('Protecta EVO Edge'),
('Protecta Sidekick'),
('Rodent Cafe'),
('Sentry'),
('Sentry Plus'),
('Striker'),
('Trakka'),
('Tunnel'),
('Wasptek'),
('ZIP tunnel'),
('Other');

-- 10 Users (1 Super Admin, 3 Coordinators, 6 Operators)
INSERT INTO Users (username, email, password_hash, first_name, last_name, phone_number, emergency_contact_name, emergency_contact_phone_number, emergency_contact_relationship, is_super_admin, account_status) VALUES
('admin_main', 'admin@pf.org.nz', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Super', 'Admin', '021000', 'Jane', '111', 'Partner', TRUE, 'Active'),
('alice_coord', 'alice@waitakere.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Alice', 'Green', '021001', 'Bob', '112', 'Spouse', FALSE, 'Active'),
('bob_coord', 'bob@coast.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Bob', 'Brown', '021002', 'Jill', '113', 'Friend', FALSE, 'Active'),
('charlie_coord', 'charlie@valley.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Charlie', 'White', '021003', 'Jan', '114', 'Parent', FALSE, 'Active'),
('op_dave', 'dave@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Dave', 'Miller', '021004', 'Eve', '115', 'Sibling', FALSE, 'Active'),
('op_eve', 'eve@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Eve', 'Smith', '021005', 'Dave', '116', 'Sibling', FALSE, 'Active'),
('op_frank', 'frank@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Frank', 'Jones', '021006', 'Grace', '117', 'Partner', FALSE, 'Active'),
('op_grace', 'grace@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Grace', 'Hill', '021007', 'Frank', '118', 'Partner', FALSE, 'Active'),
('op_heidi', 'heidi@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Heidi', 'Vogel', '021008', 'Ivan', '119', 'Spouse', FALSE, 'Active'),
('op_ivan', 'ivan@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Ivan', 'Vogel', '021009', 'Heidi', '120', 'Spouse', FALSE, 'Active'),

-- Additional Super Admins (2)
('admin_two', 'admin2@pf.org.nz', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Sam', 'Admin', '021010', 'Alex', '201', 'Friend', TRUE, 'Active'),
('admin_three', 'admin3@pf.org.nz', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Pat', 'Admin', '021011', 'Casey', '202', 'Partner', TRUE, 'Active'),

-- Additional Coordinators (5)
('donna_coord', 'donna@waitakere.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Donna', 'Taylor', '021012', 'Lee', '203', 'Partner', FALSE, 'Active'),
('eric_coord', 'eric@coast.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Eric', 'Cole', '021013', 'Mia', '204', 'Spouse', FALSE, 'Active'),
('fiona_coord', 'fiona@valley.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Fiona', 'Reid', '021014', 'Noah', '205', 'Friend', FALSE, 'Active'),
('george_coord', 'george@valley.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'George', 'Ng', '021015', 'Ivy', '206', 'Sibling', FALSE, 'Active'),
('hannah_coord', 'hannah@coast.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Hannah', 'Park', '021016', 'Owen', '207', 'Parent', FALSE, 'Active'),

-- Additional Operators (9)
('op_jack', 'jack@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Jack', 'Turner', '021017', 'Liam', '208', 'Friend', FALSE, 'Active'),
('op_kim', 'kim@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Kim', 'Nguyen', '021018', 'Maya', '209', 'Spouse', FALSE, 'Active'),
('op_luke', 'luke@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Luke', 'Wong', '021019', 'Zoe', '210', 'Partner', FALSE, 'Active'),
('op_maya', 'maya@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Maya', 'Singh', '021020', 'Ravi', '211', 'Sibling', FALSE, 'Active'),
('op_noah', 'noah@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Noah', 'Brown', '021021', 'Ella', '212', 'Friend', FALSE, 'Active'),
('op_olivia', 'olivia@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Olivia', 'Green', '021022', 'Sam', '213', 'Parent', FALSE, 'Active'),
('op_paul', 'paul@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Paul', 'Adams', '021023', 'Nina', '214', 'Partner', FALSE, 'Active'),
('op_quinn', 'quinn@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Quinn', 'Lee', '021024', 'Omar', '215', 'Friend', FALSE, 'Active'),
('op_rachel', 'rachel@work.com', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Rachel', 'Kim', '021025', 'Ben', '216', 'Sibling', FALSE, 'Active'),

-- Observers (20) - realistic names/emails
('observer1', 'sarah.jones@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Sarah', 'Jones', '021026', 'Tess', '217', 'Friend', FALSE, 'Active'),
('observer2', 'michael.brown@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Michael', 'Brown', '021027', 'Maya', '218', 'Sibling', FALSE, 'Active'),
('observer3', 'emma.wilson@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Emma', 'Wilson', '021028', 'Liam', '219', 'Partner', FALSE, 'Active'),
('observer4', 'jack.thompson@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Jack', 'Thompson', '021029', 'Nora', '220', 'Parent', FALSE, 'Active'),
('observer5', 'chloe.martin@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Chloe', 'Martin', '021030', 'Ollie', '221', 'Friend', FALSE, 'Active'),
('observer6', 'thomas.walker@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Thomas', 'Walker', '021031', 'Pia', '222', 'Partner', FALSE, 'Active'),
('observer7', 'megan.scott@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Megan', 'Scott', '021032', 'Quinn', '223', 'Sibling', FALSE, 'Active'),
('observer8', 'ryan.taylor@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Ryan', 'Taylor', '021033', 'Rae', '224', 'Friend', FALSE, 'Active'),
('observer9', 'laura.king@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Laura', 'King', '021034', 'Sam', '225', 'Parent', FALSE, 'Active'),
('observer10', 'matthew.evans@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Matthew', 'Evans', '021035', 'Tara', '226', 'Friend', FALSE, 'Active'),
('observer11', 'hannah.wright@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Hannah', 'Wright', '021036', 'Uma', '227', 'Partner', FALSE, 'Active'),
('observer12', 'oliver.harris@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Oliver', 'Harris', '021037', 'Vik', '228', 'Sibling', FALSE, 'Active'),
('observer13', 'zoe.campbell@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Zoe', 'Campbell', '021038', 'Wendy', '229', 'Parent', FALSE, 'Active'),
('observer14', 'liam.stewart@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Liam', 'Stewart', '021039', 'Xander', '230', 'Friend', FALSE, 'Active'),
('observer15', 'jessica.reed@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Jessica', 'Reed', '021040', 'Yara', '231', 'Partner', FALSE, 'Active'),
('observer16', 'daniel.hughes@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Daniel', 'Hughes', '021041', 'Zane', '232', 'Sibling', FALSE, 'Active'),
('observer17', 'sophie.murray@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Sophie', 'Murray', '021042', 'Abby', '233', 'Friend', FALSE, 'Active'),
('observer18', 'ethan.clark@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Ethan', 'Clark', '021043', 'Brad', '234', 'Parent', FALSE, 'Active'),
('observer19', 'amber.bennett@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Amber', 'Bennett', '021044', 'Cleo', '235', 'Partner', FALSE, 'Active'),
('observer20', 'benjamin.young@example.org', '$2b$12$BXkTBJ7.3GKhdwMlSAl7.egTk0qmfzsqx81G87wEJJ/Ok/2qxlqIW', 'Benjamin', 'Young', '021045', 'Drew', '236', 'Friend', FALSE, 'Active');

-- 3 Groups
INSERT INTO Groups (name, description, charitable_name, charity_registration_number, is_public, status, created_by) VALUES
('Waitakere Guardians', 'Forest protection', 'Waitakere Trust', 'CC12345', TRUE, 'Active', 1),
('Coastal Pests', 'Dune restoration', NULL, NULL, FALSE, 'Active', 1),
('Valley Predator Free', 'Farm land trapping', 'Valley Trust', 'CC99999', TRUE, 'Active', 1);

-- 10 Group Memberships
INSERT INTO Group_Members (group_id, user_id, role) VALUES 
(1, 2, 'Coordinator'), (1, 5, 'Operator'), (1, 6, 'Operator'),
(2, 3, 'Coordinator'), (2, 7, 'Operator'), (2, 8, 'Operator'),
(3, 4, 'Coordinator'), (3, 9, 'Operator'), (3, 10, 'Operator'),
(1, 10, 'Observer');

-- 5 Trap Lines and 5 Bait Station Lines
INSERT INTO Line (group_id, name, type) VALUES 
(1, 'WR-T1', 'Trap'), (1, 'WR-B1', 'Bait'),
(2, 'CP-T1', 'Trap'), (2, 'CP-B1', 'Bait'),
(3, 'VP-T1', 'Trap'), (3, 'VP-B1', 'Bait'),
(1, 'WR-T2', 'Trap'), (2, 'CP-B2', 'Bait'),
(3, 'VP-T2', 'Trap'), (1, 'WR-B2', 'Bait');

-- 10 Traps
INSERT INTO Traps (code, trap_type_id, line_id, latitude, longitude) VALUES
('T01', 1, 1, -36.9, 174.5), ('T02', 2, 1, -36.91, 174.51),
('T03', 3, 3, -36.92, 174.52), ('T04', 4, 3, -36.93, 174.53),
('T05', 5, 5, -36.94, 174.54), ('T06', 6, 5, -36.95, 174.55),
('T07', 2, 7, -36.96, 174.56), ('T08', 3, 7, -36.97, 174.57),
('T09', 4, 9, -36.98, 174.58), ('T10', 5, 9, -36.99, 174.59);

-- 10 Bait Stations
INSERT INTO Bait_Stations (code, line_id, latitude, longitude, bait_station_type_id) VALUES
('B01', 2, -36.8, 174.4, 1), ('B02', 2, -36.81, 174.41, 1),
('B03', 4, -36.82, 174.42, 2), ('B04', 4, -36.83, 174.43, 1),
('B05', 6, -36.84, 174.44, 1), ('B06', 6, -36.85, 174.45, 1),
('B07', 8, -36.86, 174.46, 3), ('B08', 8, -36.87, 174.47, 4),
('B09', 10, -36.88, 174.48, 1), ('B10', 10, -36.89, 174.49, 1);

-- 10 Trap Catches
INSERT INTO Trap_Catches (trap_id, recorded_by, date, species_caught_id, sex, maturity, trap_status_id, rebaited, bait_type_id, trap_condition) VALUES
(1, 5, '2024-05-01', 1, 'Male', 'Adult', 1, 'Yes', 1, 'OK'),
(2, 5, '2024-06-01', 2, 'Female', 'Juvenile', 2, 'No', 2, 'OK'),
(3, 7, '2024-07-01', 3, 'Male', 'Adult', 1, 'Yes', 3, 'OK'),
(4, 7, '2024-08-01', 4, 'None', 'None', 2, 'No', 4, 'OK'),
(5, 9, '2025-01-01', 5, 'Female', 'Adult', 1, 'Yes', 5, 'OK'),
(6, 9, '2025-02-01', 1, 'Male', 'Juvenile', 2, 'Yes', 1, 'OK'),
(7, 5, '2025-03-01', 1, 'Female', 'Adult', 2, 'Yes', 1, 'OK'),
(8, 7, '2025-04-01', 3, 'Male', 'Adult', 2, 'Yes', 3, 'OK'),
(9, 9, '2026-01-01', 5, 'Male', 'Adult', 2, 'Yes', 5, 'OK'),
(10, 5, '2026-05-01', 1, 'Female', 'Adult', 2, 'Yes', 1, 'OK');

-- 10 Bait Station Records
INSERT INTO Bait_Station_Records (station_id, recorded_by, date_recorded, target_species_id, active_ingredient, formulation, concentration, bait_remaining, bait_added) VALUES
(1, 6, '2025-05-01', 1, 'Brodifacoum', 'Pellet', 0.05, 0.2, 0.8),
(2, 6, '2025-06-01', 2, 'Diphacinone', 'Cereal', 0.05, 0.1, 0.9),
(3, 8, '2025-07-01', 3, 'Diphacinone', 'Paste', 0.05, 0.3, 0.7),
(4, 8, '2025-08-01', 4, 'Cholecalciferol', 'Block', 0.10, 0.0, 1.0),
(5, 10, '2025-09-01', 3, 'Brodifacoum', 'Pellet', 0.05, 0.5, 0.5),
(6, 10, '2026-01-01', 2, 'Brodifacoum', 'Pellet', 0.05, 0.2, 0.8),
(7, 6, '2026-02-01', 3, 'Diphacinone', 'Cereal', 0.05, 0.1, 0.9),
(8, 8, '2026-03-01', 4, 'Coumateralyl', 'Pellet', 0.05, 0.4, 0.6),
(9, 10, '2026-04-01', 3, 'Brodifacoum', 'Pellet', 0.05, 0.2, 0.8),
(10, 6, '2026-05-01', 2, 'Bromadiolone', 'Paste', 0.10, 0.0, 1.0);
-- 10 Donations
INSERT INTO Donations (group_id, amount, donation_type, donor_name, donor_email, is_anonymous) VALUES
(1, 50.00, 'Group Donation', 'John Supporter', 'john@test.com', FALSE),
(2, 20.00, 'Group Donation', 'Anon', 'anon@test.com', TRUE),
(NULL, 100.00, 'Platform Support', 'Big Corp', 'corp@test.com', FALSE),
(3, 10.00, 'Group Donation', 'Sarah Lee', 'sarah@test.com', FALSE),
(1, 25.00, 'Group Donation', 'Supporter B', 'b@test.com', FALSE),
(2, 40.00, 'Group Donation', 'C Supporter', 'c@test.com', FALSE),
(3, 15.00, 'Group Donation', 'D Supporter', 'd@test.com', FALSE),
(NULL, 5.00, 'General Support', 'E Supporter', 'e@test.com', FALSE),
(1, 30.00, 'Group Donation', 'F Supporter', 'f@test.com', FALSE),
(2, 50.00, 'Group Donation', 'G Supporter', 'g@test.com', FALSE);
-- Knowledge_Categories
INSERT INTO Knowledge_Categories (name) VALUES 
('Trap Management'), ('Bait Station Safety'), ('Species ID'), ('Seasonal Advice'), ('Field Health & Safety');
-- 10 Knowledge Hub Entries
INSERT INTO Knowledge_Entries (category_id, author_id, approved_by, title, content, status) VALUES
(1, 2, 1, 'DOC 200 Maintenance', 'Detailed steps for cleaning...', 'Published'),
(2, 3, 1, 'Bait Safety 101', 'Always wear gloves...', 'Published'),
(3, 4, 1, 'Identifying Stoats', 'Look for the black tip on tail...', 'Published'),
(4, 2, 1, 'Winter Bait Tips', 'Peanut butter freezes...', 'Published'),
(5, 3, 1, 'Health & Safety in Bush', 'Check the weather...', 'Published'),
(1, 4, 1, 'Setting A24s', 'CO2 canister safety...', 'Published'),
(2, 2, 1, 'Rodent Cafe Setup', 'Best placement strategy...', 'Published'),
(3, 3, 1, 'Rat vs Mouse Sign', 'Dropping identification...', 'Published'),
(4, 4, 1, 'Spring Pest Migration', 'Expect more stoats...', 'Published'),
(5, 2, 1, 'Emergency Comms', 'Satellite phone guide...', 'Published');

-- 10 Group Updates
INSERT INTO Group_Updates (group_id, author_id, title, content, status) VALUES
(1, 2, 'Great Success!', '10 rats caught this week.', 'Published'),
(1, 2, 'Meeting Monday', 'At the community hall.', 'Published'),
(2, 3, 'Beach Cleanup', 'Combining with trapping.', 'Published'),
(2, 3, 'Bait Delivery', 'Picking up at 10am.', 'Published'),
(3, 4, 'Valley News', 'New line established.', 'Published'),
(3, 4, 'Funding Alert', 'We got the grant!', 'Published'),
(1, 2, 'Training Day', 'Learn to use DOC 250s.', 'Published'),
(2, 3, 'Volunteer Wanted', 'Help needed for Line B.', 'Published'),
(3, 4, 'Stoat Sighting', 'Watch the north fence.', 'Published'),
(1, 2, 'Seasonal Notice', 'Bait change to egg.', 'Published');

-- 10 Point Records
INSERT INTO User_Points (user_id, cumulative_points, notes) VALUES 
(2, 3, 'Trap catches'), (3, 5, 'Bait station maintenance'), (4, 2, 'Trap catches'), (5, 4, 'Bait station maintenance'), (6, 8, 'Trap catches'), 
(7, 6, 'Bait station maintenance'), (8, 4, 'Trap catches'), (9, 8, 'Bait station maintenance'), (10, 6, 'Trap catches'), (1, 3, 'Bait station maintenance');

-- =========================
-- GALLERY THEMES (Pre-made)
-- =========================
INSERT INTO Group_Themes (group_id, theme_name, settings, is_active, created_by)
VALUES 
(NULL, 'Forest Canopy', 
 '{
  "colors": {"primary": "#2D5A27", "secondary": "#E8F5BD", "background": "#F9FAF8", "text": "#1A1A1A"},
  "visuals": {"font": "Verdana, sans-serif", "button": "rounded", "banner": "/static/themes/forest.jpg"},
  "layout": {"template": "sidebar"}
 }', TRUE, 1),

(NULL, 'Coastal Scrub', 
 '{
  "colors": {"primary": "#007E6E", "secondary": "#D7C097", "background": "#FFFFFF", "text": "#212121"},
  "visuals": {"font": "Arial, sans-serif", "button": "pill", "banner": "/static/themes/coastal.jpg"},
  "layout": {"template": "grid"}
 }', TRUE, 1),

(NULL, 'Alpine Tussock', 
 '{
  "colors": {"primary": "#8A5F41", "secondary": "#CCD67F", "background": "#F3E4C9", "text": "#3E2723"},
  "visuals": {"font": "Trebuchet MS, sans-serif", "button": "square", "banner": "/static/themes/alpine.jpg"},
  "layout": {"template": "centered"}
 }', TRUE, 1);

 -- =========================
-- ACTIVE GROUP THEMES
-- =========================
INSERT INTO Group_Themes (group_id, theme_name, settings, is_active, version_number, created_by)
VALUES 
-- Waitakere Guardians using a modified 'Forest' theme
(1, 'Waitakere Custom', 
 '{
  "colors": {"primary": "#1B331A", "secondary": "#C5E1A5", "background": "#F1F8E9", "text": "#000000"},
  "visuals": {"font": "Verdana, sans-serif", "button": "rounded", "banner": "/static/uploads/waitakere_banner.jpg", "logo": "/static/uploads/waitakere_logo.png"},
  "layout": {"template": "sidebar"}
 }', TRUE, 2, 2),

-- Coastal Pests using the standard 'Coastal' theme
(2, 'Coastal Standard', 
 '{
  "colors": {"primary": "#007E6E", "secondary": "#D7C097", "background": "#FFFFFF", "text": "#212121"},
  "visuals": {"font": "Arial, sans-serif", "button": "pill", "banner": "/static/themes/coastal.jpg"},
  "layout": {"template": "grid"}
 }', TRUE, 1, 3),

-- Valley Predator Free using a high-contrast 'Alpine' variation
(3, 'Valley High-Vis', 
 '{
  "colors": {"primary": "#BF360C", "secondary": "#FFCCBC", "background": "#FFFFFF", "text": "#263238"},
  "visuals": {"font": "Helvetica, sans-serif", "button": "square", "banner": "/static/themes/alpine.jpg"},
  "layout": {"template": "centered"}
 }', TRUE, 1, 4);

 -- An old version of Waitakere's theme (Version 1)
INSERT INTO Group_Themes (group_id, theme_name, settings, is_active, version_number, created_by)
VALUES 
(1, 'Waitakere Old', 
 '{
  "colors": {"primary": "#4CAF50", "secondary": "#8BC34A", "background": "#FFFFFF", "text": "#333333"},
  "visuals": {"font": "Arial", "button": "rounded"},
  "layout": {"template": "grid"}
 }', FALSE, 1, 2);