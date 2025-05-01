# mysql_bank_database.py
from datetime import datetime, timedelta
import os
from turtle import st
import mysql
from mysql_config import MySQLDatabase

class UserManager:
    def __init__(self, conn):
        self.conn = conn
    
    def create_users_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
        ''')
        self.conn.commit()
    
    def add_user(self, username, email, password_hash, role='user'):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            ''', (username, email, password_hash, role))
            self.conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error adding user: {err}")
            return None
    
    def get_user_by_username(self, username):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username=%s', (username,))
        return cursor.fetchone()
    
    def verify_user(self, username, password_hash):
        user = self.get_user_by_username(username)
        if user and user['password_hash'] == password_hash:
            return user
        return None

class BankDatabase:
    def __init__(self):
        self.db = MySQLDatabase()
        self.conn = self.db.connect()
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor(dictionary=True)
        
        # Table Clients
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE,
            phone VARCHAR(50),
            type VARCHAR(50),
            status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Table IBAN
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ibans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            client_id INT NOT NULL,
            iban VARCHAR(34) UNIQUE NOT NULL,
            currency VARCHAR(3),
            type VARCHAR(50),
            balance DECIMAL(15,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
        )
        ''')
        
        # Table Transactions
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            iban_id INT NOT NULL,
            client_id INT NOT NULL,
            type VARCHAR(50) NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (iban_id) REFERENCES ibans (id) ON DELETE CASCADE,
            FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
        )
        ''')
        
        # Table Users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        self.conn.commit()
    
    # Méthodes pour les clients (adaptées pour MySQL)
    def add_client(self, first_name, last_name, email, phone, client_type, status):
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute('''
            INSERT INTO clients (first_name, last_name, email, phone, type, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''', (first_name, last_name, email, phone, client_type, status))
            self.conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None
    
    def get_client_by_id(self, client_id):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM clients WHERE id=%s', (client_id,))
        return cursor.fetchone()
    
    def get_all_clients(self):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM clients ORDER BY last_name, first_name')
        return cursor.fetchall()
    
    # Méthodes pour les IBAN
    def add_iban(self, client_id, iban, currency, account_type, balance=0):
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute('''
            INSERT INTO ibans (client_id, iban, currency, type, balance)
            VALUES (%s, %s, %s, %s, %s)
            ''', (client_id, iban, currency, account_type, balance))
            self.conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None
    
    def get_ibans_by_client(self, client_id):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM ibans WHERE client_id=%s', (client_id,))
        return cursor.fetchall()
    
    # Méthodes pour les transactions
    def deposit(self, iban_id, amount, description=""):
        cursor = self.conn.cursor(dictionary=True)
        try:
            # Récupérer le client_id associé à l'IBAN
            cursor.execute('SELECT client_id FROM ibans WHERE id=%s', (iban_id,))
            iban = cursor.fetchone()
            if not iban:
                return False
            
            # Démarrer une transaction
            self.conn.start_transaction()
            
            # Ajouter la transaction
            cursor.execute('''
            INSERT INTO transactions (iban_id, client_id, type, amount, description)
            VALUES (%s, %s, 'Dépôt', %s, %s)
            ''', (iban_id, iban['client_id'], amount, description))
            
            # Mettre à jour le solde
            cursor.execute('''
            UPDATE ibans 
            SET balance = balance + %s
            WHERE id=%s
            ''', (amount, iban_id))
            
            self.conn.commit()
            return True
        except mysql.connector.Error as err:
            self.conn.rollback()
            print(f"Error during deposit: {err}")
            return False
    
    def get_recent_transactions(self, limit=5):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute('''
        SELECT t.*, i.iban, c.first_name, c.last_name
        FROM transactions t
        JOIN ibans i ON t.iban_id = i.id
        JOIN clients c ON t.client_id = c.id
        ORDER BY t.date DESC
        LIMIT %s
        ''', (limit,))
        return cursor.fetchall()
    
    # Méthodes pour les utilisateurs
    def add_user(self, username, email, password_hash, role='user'):
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            ''', (username, email, password_hash, role))
            self.conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None
    
    def get_user_by_username(self, username):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username=%s', (username,))
        return cursor.fetchone()
    
    def close(self):
        self.db.close()