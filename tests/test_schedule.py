import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Ajusta o caminho para importar do diretório pai

import unittest
import mysql.connector
from school_schedule import create_connection, optimize_schedule

class TestSchoolScheduler(unittest.TestCase):
    def setUp(self):
        self.conn = create_connection()

    def test_connection(self):
        self.assertIsNotNone(self.conn)

    def test_optimize_schedule(self):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO professores (nome, disponibilidade, preferencias) VALUES (%s, %s, %s)", ("Teste", "Segunda", "Matemática"))
        cursor.execute("INSERT INTO materias (nome, carga_horaria) VALUES (%s, %s)", ("Matemática", 2))
        cursor.execute("INSERT INTO turmas (nome, ano) VALUES (%s, %s)", ("Turma A", 2025))
        self.conn.commit()
        optimize_schedule(self.conn)
        cursor.execute("SELECT COUNT(*) FROM cronogramas")
        self.assertGreater(cursor.fetchone()[0], 0)

    def tearDown(self):
        self.conn.close()

if __name__ == '__main__':
    unittest.main()