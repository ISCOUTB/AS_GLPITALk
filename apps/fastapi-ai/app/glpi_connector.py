"""
Módulo para conectar con la base de datos de GLPI
"""
import pymysql
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class GLPIConnector:
    """Gestor de conexión con base de datos GLPI"""
    
    def __init__(self):
        self.host = os.getenv("GLPI_DB_HOST", "glpi-mariadb")
        self.user = os.getenv("GLPI_DB_USER", "glpi_user")
        self.password = os.getenv("GLPI_DB_PASSWORD", "glpi_password_segura")
        self.database = os.getenv("GLPI_DB_NAME", "glpidb")
        self.port = int(os.getenv("GLPI_DB_PORT", 3306))
        self.connection = None
    
    def connect(self):
        """Establece conexión con GLPI"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except pymysql.Error as e:
            print(f"Error de conexión GLPI: {e}")
            return False
    
    def disconnect(self):
        """Cierra la conexión"""
        if self.connection:
            self.connection.close()
    
    def get_user_tickets(self, phone_number: str) -> List[Dict]:
        """Obtiene tickets de un usuario por número de teléfono"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                # Buscar todos los usuarios asociados al teléfono
                query = """
                    SELECT u.id FROM glpi_users u
                    WHERE u.phone LIKE %s OR u.phone2 LIKE %s OR u.mobile LIKE %s
                """
                cursor.execute(query, (f"%{phone_number}%", f"%{phone_number}%", f"%{phone_number}%"))
                users = cursor.fetchall()

                if not users:
                    return []

                user_ids = [user['id'] for user in users]
                placeholders = ", ".join(["%s"] * len(user_ids))
                user_ids_tuple = tuple(user_ids)
                
                # Obtener tickets del usuario
                tickets_query = """
                    SELECT t.id, t.name, t.status, t.date_creation
                    FROM glpi_tickets t
                    JOIN glpi_tickets_users tu ON tu.tickets_id = t.id
                    WHERE tu.users_id IN (%s) AND tu.type = 1
                    ORDER BY t.date_creation DESC
                    LIMIT 10
                """
                query = tickets_query.replace('(%s)', f'({placeholders})')
                cursor.execute(query, user_ids_tuple)
                tickets = cursor.fetchall()
                
                return tickets
        except Exception as e:
            print(f"Error al obtener tickets: {e}")
            return []
    
    def get_ticket_details(self, ticket_id: int) -> Optional[Dict]:
        """Obtiene detalles de un ticket específico"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                query = """
                    SELECT t.id, t.name, t.status, t.date_creation,
                           t.content, u.name as requester_name
                    FROM glpi_tickets t
                    LEFT JOIN glpi_tickets_users tu ON tu.tickets_id = t.id AND tu.type = 1
                    LEFT JOIN glpi_users u ON tu.users_id = u.id
                    WHERE t.id = %s
                """
                cursor.execute(query, (ticket_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error al obtener detalles del ticket: {e}")
            return None
    
    def create_ticket(self, phone_number: str, title: str, description: str) -> Optional[int]:
        """Crea un nuevo ticket"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                # Buscar usuario
                query = "SELECT id FROM glpi_users WHERE phone LIKE %s OR phone2 LIKE %s OR mobile LIKE %s LIMIT 1"
                cursor.execute(query, (f"%{phone_number}%", f"%{phone_number}%", f"%{phone_number}%"))
                user = cursor.fetchone()
                
                if not user:
                    return None
                
                # Crear ticket
                insert_query = """
                    INSERT INTO glpi_tickets 
                    (name, content, status, date_creation)
                    VALUES (%s, %s, 1, NOW())
                """
                cursor.execute(insert_query, (title, description))
                ticket_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO glpi_tickets_users (tickets_id, users_id, type, use_notification) VALUES (%s, %s, 1, 1)",
                    (ticket_id, user['id'])
                )
                self.connection.commit()
                return ticket_id
        except Exception as e:
            print(f"Error al crear ticket: {e}")
            return None
    
    def get_ticket_status_summary(self, phone_number: str) -> Dict:
        """Obtiene resumen de estados de tickets"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                # Buscar todos los usuarios asociados al teléfono
                query = """
                    SELECT u.id FROM glpi_users u
                    WHERE u.phone LIKE %s OR u.phone2 LIKE %s OR u.mobile LIKE %s
                """
                cursor.execute(query, (f"%{phone_number}%", f"%{phone_number}%", f"%{phone_number}%"))
                users = cursor.fetchall()

                if not users:
                    return {}

                user_ids = [user['id'] for user in users]
                placeholders = ", ".join(["%s"] * len(user_ids))
                user_ids_tuple = tuple(user_ids)

                # Contar tickets por estado (para todos los user IDs encontrados)
                summary_query = """
                    SELECT 
                        SUM(CASE WHEN t.status = 1 THEN 1 ELSE 0 END) as new,
                        SUM(CASE WHEN t.status = 2 THEN 1 ELSE 0 END) as assigned,
                        SUM(CASE WHEN t.status = 3 THEN 1 ELSE 0 END) as planned,
                        SUM(CASE WHEN t.status = 4 THEN 1 ELSE 0 END) as waiting,
                        SUM(CASE WHEN t.status = 5 THEN 1 ELSE 0 END) as solved,
                        SUM(CASE WHEN t.status = 6 THEN 1 ELSE 0 END) as closed
                    FROM glpi_tickets t
                    JOIN glpi_tickets_users tu ON tu.tickets_id = t.id AND tu.type = 1
                    WHERE tu.users_id IN (%s)
                """
                query = summary_query.replace('(%s)', f'({placeholders})')
                cursor.execute(query, user_ids_tuple)
                result = cursor.fetchone()
                
                return {
                    "new": result.get('new', 0) or 0,
                    "assigned": result.get('assigned', 0) or 0,
                    "planned": result.get('planned', 0) or 0,
                    "waiting": result.get('waiting', 0) or 0,
                    "solved": result.get('solved', 0) or 0,
                    "closed": result.get('closed', 0) or 0,
                }
        except Exception as e:
            print(f"Error al obtener resumen: {e}")
            return {}

    def _is_safe_select_query(self, sql: str) -> bool:
        """Valida que la consulta SQL sea una lectura segura de solo SELECT."""
        sql_lower = sql.strip().lower()
        if not sql_lower.startswith("select"):
            return False
        if ";" in sql_lower:
            return False
        forbidden = ["insert", "update", "delete", "drop", "alter", "create", "truncate", "replace", "grant", "revoke", "commit", "rollback", "use", "lock", "set"]
        return not any(word in sql_lower for word in forbidden)

    def execute_select_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """Ejecuta una consulta SELECT segura y devuelve los resultados."""
        if not self._is_safe_select_query(sql):
            raise ValueError("SQL no segura o no permitida")

        try:
            if not self.connection:
                self.connect()

            with self.connection.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except Exception as e:
            print(f"Error al ejecutar query SQL: {e}")
            raise
