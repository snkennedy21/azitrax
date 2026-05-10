-- Create test database for pytest
-- This script runs automatically when the PostgreSQL container starts
-- for the first time (only if the database doesn't already exist)

CREATE DATABASE vector_test OWNER vector;
