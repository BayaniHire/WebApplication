-- Create Database
CREATE DATABASE IF NOT EXISTS bayanihire_webapp_database;
USE bayanihire_webapp_database;

-- Table 1: account_information
CREATE TABLE account_information (
    account_id INT(11) NOT NULL AUTO_INCREMENT,
    username VARCHAR(45) NOT NULL,
    password VARCHAR(45) NOT NULL,
    last_name VARCHAR(45),
    first_name VARCHAR(45),
    middle_name VARCHAR(45),
    house_no VARCHAR(45),
    province VARCHAR(45),
    barangay VARCHAR(45),
    street_village VARCHAR(45),
    city_municipality VARCHAR(45),
    state VARCHAR(45),
    zipcode INT,
    email VARCHAR(45),
    mobile_number BIGINT,
    birth_date DATE,
    age INT,
    gender VARCHAR(45),
    PRIMARY KEY (account_id)
) ENGINE=InnoDB;

-- Table 2: account_storage
CREATE TABLE account_storage (
    role_id INT NOT NULL AUTO_INCREMENT,
    account_id INT(11),
    role VARCHAR(45),
    account_status VARCHAR(11),
    PRIMARY KEY (role_id),
    CONSTRAINT fk_account FOREIGN KEY (account_id) 
        REFERENCES account_information(account_id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Table 3: job_details_and_requirements
CREATE TABLE job_details_and_requirements (
    job_id INT NOT NULL AUTO_INCREMENT,
    account_id INT(11),
    job_title VARCHAR(100),
    job_company VARCHAR(50),
    job_description VARCHAR(1500),
    job_benefits VARCHAR(1500),
    job_requirements VARCHAR(500),
    job_status VARCHAR(7),
    job_date_published DATE,
    PRIMARY KEY (job_id),
    CONSTRAINT fk_job_account FOREIGN KEY (account_id) 
        REFERENCES account_information(account_id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Table 4: interview_storage
CREATE TABLE interview_storage (
    interview_applicant_id INT NOT NULL AUTO_INCREMENT,
    account_id INT(11),
    role_id INT,
    interview_schedule_date DATE,
    interviewer_schedule_status VARCHAR(10),
    applicant_schedule_date DATE,
    admin_message VARCHAR(1500),
    interviewer_feedback VARCHAR(1500),
    interviewer_feedback_status VARCHAR(20),
    PRIMARY KEY (interview_applicant_id),
    CONSTRAINT fk_interview_account FOREIGN KEY (account_id) 
        REFERENCES account_information(account_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_interview_role FOREIGN KEY (role_id) 
        REFERENCES account_storage(role_id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Table 5: list_of_applicants_with_status_and_credentials
CREATE TABLE list_of_applicants_with_status_and_credentials (
    applicant_status_id INT NOT NULL AUTO_INCREMENT,
    role_id INT,
    account_id INT,
    job_id INT,
    interview_applicant_id INT,
    applicant_status VARCHAR(30),
    credentials LONGBLOB,
    file_metadata TEXT,
    submission_date DATE,
    PRIMARY KEY (applicant_status_id),
    CONSTRAINT fk_applicant_role FOREIGN KEY (role_id) 
        REFERENCES account_storage(role_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_applicant_account FOREIGN KEY (account_id) 
        REFERENCES account_information(account_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_applicant_job FOREIGN KEY (job_id) 
        REFERENCES job_details_and_requirements(job_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_applicant_interview FOREIGN KEY (interview_applicant_id) 
        REFERENCES interview_storage(interview_applicant_id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;
