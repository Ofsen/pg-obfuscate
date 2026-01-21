-- Create users table
CREATE TABLE
    users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        email VARCHAR(100) NOT NULL,
        phone VARCHAR(20),
        date_of_birth DATE,
        account_balance NUMERIC(10, 2),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW (),
        updated_at TIMESTAMP DEFAULT NOW ()
    );

-- Create orders table (tests foreign keys)
CREATE TABLE
    orders (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users (id),
        order_total NUMERIC(10, 2) NOT NULL,
        tax_amount NUMERIC(8, 2),
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT NOW ()
    );

-- Create profiles table (tests more types)
CREATE TABLE
    profiles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE REFERENCES users (id),
        bio TEXT,
        age SMALLINT,
        height REAL,
        weight DOUBLE PRECISION,
        is_verified BOOLEAN DEFAULT FALSE
    );

-- Insert test data
INSERT INTO
    users (
        username,
        email,
        phone,
        date_of_birth,
        account_balance,
        is_active,
        created_at
    )
VALUES
    (
        'alice_smith',
        'alice@example.com',
        '555-0101',
        '1990-03-15',
        1250.50,
        TRUE,
        '2024-01-01'
    ),
    (
        'bob_johnson',
        'bob@example.com',
        '555-0102',
        '1985-07-22',
        3450.75,
        TRUE,
        '2024-01-05'
    ),
    (
        'carol_white',
        'carol@example.com',
        '555-0103',
        '1992-11-30',
        500.00,
        FALSE,
        '2024-01-10'
    ),
    (
        'david_brown',
        'david@example.com',
        '555-0104',
        '1988-05-10',
        7890.25,
        TRUE,
        '2024-01-15'
    ),
    (
        'eve_davis',
        'eve@example.com',
        NULL,
        '1995-12-25',
        2100.00,
        TRUE,
        '2024-01-20'
    );

INSERT INTO
    orders (
        user_id,
        order_total,
        tax_amount,
        status,
        created_at
    )
VALUES
    (1, 100.00, 8.50, 'completed', '2024-01-02'),
    (1, 250.00, 21.25, 'completed', '2024-01-08'),
    (2, 500.00, 42.50, 'pending', '2024-01-16'),
    (3, 75.50, 6.42, 'completed', '2024-01-12'),
    (4, 1200.00, 102.00, 'pending', '2024-01-18'),
    (4, 300.00, 25.50, 'completed', '2024-01-20'),
    (5, 450.00, 38.25, 'shipped', '2024-01-22');

INSERT INTO
    profiles (user_id, bio, age, height, weight, is_verified)
VALUES
    (
        1,
        'Software engineer based in SF',
        34,
        5.8,
        170.5,
        TRUE
    ),
    (2, 'Product manager', 39, 5.9, 185.0, TRUE),
    (3, 'Designer and artist', 32, 5.6, 155.5, FALSE),
    (4, 'Data scientist', 36, 6.0, 195.5, TRUE),
    (5, 'Marketing specialist', 29, 5.7, 160.0, FALSE);

-- Verify data
SELECT
    COUNT(*)
FROM
    users;

SELECT
    COUNT(*)
FROM
    orders;

SELECT
    COUNT(*)
FROM
    profiles;