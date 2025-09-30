import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Ajusta o caminho para importar do diretório pai

import unittest
import mysql.connector
from school_schedule import create_connection, optimize_schedule, create_tables  # Import create_tables

class TestSchoolScheduler(unittest.TestCase):
    def setUp(self):
        self.conn = create_connection()
        print("Conexão estabelecida para o teste")
        # Criar tabelas uma vez no setUp para todos os testes
        create_tables(self.conn)
        print("Tabelas criadas para o teste")

    def test_connection(self):
        self.assertIsNotNone(self.conn)
        print("Teste de conexão passou")

    def test_optimize_schedule(self):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO professores (nome, disponibilidade, preferencias) VALUES (%s, %s, %s)", ("Teste", "Segunda", "Matemática"))
        cursor.execute("INSERT INTO materias (nome, carga_horaria) VALUES (%s, %s)", ("Matemática", 2))
        cursor.execute("INSERT INTO turmas (nome, ano) VALUES (%s, %s)", ("Turma A", 2025))
        self.conn.commit()
        print("Dados inseridos com sucesso")
        
        optimize_schedule(self.conn)
        cursor.execute("SELECT COUNT(*) FROM cronogramas")
        count = cursor.fetchone()[0]
        print(f"Registros no cronograma: {count}")
        self.assertGreater(count, 0)
        print("Teste de otimização passou")

    def tearDown(self):
        try:
            cursor = self.conn.cursor()
            # Deletar em ordem reversa para evitar foreign key errors: cronogramas primeiro, depois pais
            cursor.execute("DELETE FROM cronogramas")
            cursor.execute("DELETE FROM professores WHERE nome = 'Teste'")
            cursor.execute("DELETE FROM materias WHERE nome = 'Matemática'")
            cursor.execute("DELETE FROM turmas WHERE nome = 'Turma A'")
            self.conn.commit()
            print("Dados limpos com sucesso")
        except mysql.connector.Error as e:
            print(f"Erro ao limpar dados (ignorado em CI): {e}")
        finally:
            self.conn.close()
            print("Conexão fechada")

if __name__ == '__main__':
    unittest.main()