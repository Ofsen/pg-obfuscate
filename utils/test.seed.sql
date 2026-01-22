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
        status VARCHAR(100) DEFAULT 'pending',
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

-- Create strategy_complex_test table for all strategies
CREATE TABLE
    strategy_complex_test (
        id SERIAL PRIMARY KEY,
        h_text TEXT,
        f_email VARCHAR(100),
        f_name VARCHAR(100),
        f_first_name VARCHAR(50),
        f_last_name VARCHAR(50),
        f_phone VARCHAR(50),
        f_address TEXT,
        f_company VARCHAR(100),
        f_text TEXT,
        f_city VARCHAR(100),
        f_country VARCHAR(100),
        f_postcode VARCHAR(20),
        f_street_address VARCHAR(200),
        f_job VARCHAR(100),
        f_url VARCHAR(200),
        f_username VARCHAR(50),
        f_uuid UUID,
        f_int INTEGER,
        f_number NUMERIC(12, 4),
        f_float REAL,
        f_decimal DECIMAL(12, 2),
        f_date DATE,
        f_datetime TIMESTAMP,
        s_null VARCHAR(50),
        s_preserve VARCHAR(50)
    );

-- Create overflow_test table
CREATE TABLE
    overflow_test (
        id SERIAL PRIMARY KEY,
        s_int SMALLINT,
        i_int INTEGER
    );

-- Insert test data for users
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

-- Insert test data for orders
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

-- Insert test data for profiles
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

-- Insert test data for strategy_complex_test
INSERT INTO
    strategy_complex_test (
        h_text,
        f_email,
        f_name,
        f_first_name,
        f_last_name,
        f_phone,
        f_address,
        f_company,
        f_text,
        f_city,
        f_country,
        f_postcode,
        f_street_address,
        f_job,
        f_url,
        f_username,
        f_uuid,
        f_int,
        f_number,
        f_float,
        f_decimal,
        f_date,
        f_datetime,
        s_null,
        s_preserve
    )
VALUES
    (
        'original text 1',
        'alice@example.com',
        'John Doe',
        'John',
        'Doe',
        '123-456-7890',
        '123 Main St, Springfield',
        'ACME Corp',
        'Lorem ipsum dolor sit amet.',
        'Springfield',
        'USA',
        '62704',
        '123 Main St',
        'Engineer',
        'https://example.com',
        'jdoe',
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        12345,
        123.4567,
        1.23,
        12.34,
        '2023-01-01',
        '2023-01-01 12:00:00',
        'keep me null please',
        'I should stay the same'
    ),
    (
        'another text',
        'test2@example.com',
        'Jane Smith',
        'Jane',
        'Smith',
        '987-654-3210',
        '456 Elm St, Shelbyville',
        'Globex',
        'Consectetur adipiscing elit.',
        'Shelbyville',
        'USA',
        '62705',
        '456 Elm St',
        'Manager',
        'https://globex.com',
        'jsmith',
        'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12',
        67890,
        678.9012,
        6.78,
        67.89,
        '2023-12-31',
        '2023-12-31 23:59:59',
        NULL,
        'unchanged'
    );

-- Insert test data for overflow_test
INSERT INTO
    overflow_test (s_int, i_int)
VALUES
    (32767, 2147483647),
    (-32768, -2147483648),
    (0, 0),
    (100, 1000000);