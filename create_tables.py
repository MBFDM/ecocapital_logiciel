# create_tables.py
from mysql_config import MySQLDatabase

def create_tables():
    db = MySQLDatabase()
    conn = db.connect()
    
    if conn is None:
        print("Échec de la connexion à la base de données")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
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
        ) ENGINE=InnoDB
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
        ) ENGINE=InnoDB
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
        ) ENGINE=InnoDB
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
        ) ENGINE=InnoDB
        ''')
        
        conn.commit()
        print("Tables créées avec succès sur Railway MySQL")
        
    except Exception as e:
        print(f"Erreur lors de la création des tables: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()