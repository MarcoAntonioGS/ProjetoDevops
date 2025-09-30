import mysql.connector
from mysql.connector import Error
import pulp
import tkinter as tk
from tkinter import messagebox, ttk
import random
from datetime import datetime, timedelta

# Configurações de conexão com o banco de dados MySQL
DB_HOST = 'localhost'
DB_USER = 'root'  # Substitua pelo seu usuário
DB_PASSWORD = '221203Ma'  # Substitua pela sua senha
DB_NAME = 'sistema_escolar'

# Função para criar a conexão com o banco de dados
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            database=DB_NAME
        )
        print("Conexão com MySQL DB bem-sucedida")
    except Error as e:
        print(f"Erro ao conectar ao MySQL DB: '{e}'")
    return connection

# Função para criar as tabelas no banco de dados
def create_tables(connection):
    cursor = connection.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS professores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        disponibilidade TEXT,
        preferencias TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        carga_horaria INT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS turmas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(50) NOT NULL,
        ano INT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cronogramas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        professor_id INT,
        materia_id INT,
        turma_id INT,
        dia_semana VARCHAR(20),
        horario_inicio TIME,
        horario_fim TIME,
        FOREIGN KEY (professor_id) REFERENCES professores(id),
        FOREIGN KEY (materia_id) REFERENCES materias(id),
        FOREIGN KEY (turma_id) REFERENCES turmas(id)
    )
    """)
    
    connection.commit()
    print("Tabelas criadas com sucesso")

# Função para otimizar o cronograma usando PuLP
def optimize_schedule(connection):
    cursor = connection.cursor()
    
    # Verificar se há dados suficientes
    cursor.execute("SELECT COUNT(*) FROM professores")
    if cursor.fetchone()[0] == 0:
        messagebox.showerror("Erro", "Nenhum professor cadastrado!")
        return
    cursor.execute("SELECT COUNT(*) FROM materias")
    if cursor.fetchone()[0] == 0:
        messagebox.showerror("Erro", "Nenhuma matéria cadastrada!")
        return
    cursor.execute("SELECT COUNT(*) FROM turmas")
    if cursor.fetchone()[0] == 0:
        messagebox.showerror("Erro", "Nenhuma turma cadastrada!")
        return
    
    cursor.execute("SELECT id, nome, disponibilidade, preferencias FROM professores")
    professores = cursor.fetchall()
    
    cursor.execute("SELECT id, nome, carga_horaria FROM materias")
    materias = cursor.fetchall()
    
    cursor.execute("SELECT id, nome FROM turmas")
    turmas = cursor.fetchall()
    
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta']
    
    horarios = [
        ('08:00:00', '09:00:00'),
        ('09:00:00', '10:00:00'),
        ('10:00:00', '11:00:00'),
        ('11:00:00', '12:00:00')
    ]
    
    prob = pulp.LpProblem("Agendamento_Escolar", pulp.LpMinimize)
    
    x = pulp.LpVariable.dicts("assign", 
                              ((p[0], m[0], t[0], d, s) 
                               for p in professores 
                               for m in materias 
                               for t in turmas 
                               for d in dias_semana 
                               for s in range(len(horarios))),
                              cat='Binary')
    
    prob += pulp.lpSum(x.values())
    
    for m_id, _, carga in materias:
        for t_id, _ in turmas:
            prob += pulp.lpSum(x[p[0], m_id, t_id, d, s] 
                               for p in professores 
                               for d in dias_semana 
                               for s in range(len(horarios))) == carga
    
    for p in professores:
        p_id = p[0]
        for d in dias_semana:
            for s in range(len(horarios)):
                prob += pulp.lpSum(x[p_id, m[0], t[0], d, s] 
                                   for m in materias 
                                   for t in turmas) <= 1
    
    for p in professores:
        p_id = p[0]
        disp = p[2].split(',') if p[2] else []
        for d in dias_semana:
            if d not in disp:
                for m in materias:
                    for t in turmas:
                        for s in range(len(horarios)):
                            prob += x[p_id, m[0], t[0], d, s] == 0
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] != 'Optimal':
        messagebox.showerror("Erro", "Não foi possível gerar um cronograma. Verifique os dados inseridos!")
        return
    
    cursor.execute("DELETE FROM cronogramas")
    for var in x:
        if pulp.value(x[var]) == 1:
            p_id, m_id, t_id, d, s = var
            inicio, fim = horarios[s]
            cursor.execute("""
            INSERT INTO cronogramas (professor_id, materia_id, turma_id, dia_semana, horario_inicio, horario_fim)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (p_id, m_id, t_id, d, inicio, fim))
    
    connection.commit()
    messagebox.showinfo("Sucesso", "Cronograma gerado com sucesso!")

# GUI para o diretor inserir dados
class SchoolApp:
    def __init__(self, root, connection):
        self.root = root
        self.conn = connection
        self.root.title("Sistema de Agendamento Escolar")
        self.root.geometry("800x600")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        # Aba Professores
        self.prof_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.prof_frame, text="Professores")
        self.setup_prof_frame()

        # Aba Matérias
        self.mat_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.mat_frame, text="Matérias")
        self.setup_mat_frame()

        # Aba Turmas
        self.tur_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tur_frame, text="Turmas")
        self.setup_tur_frame()

        # Aba Dados Cadastrados
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="Dados Cadastrados")
        self.setup_data_frame()

        # Botão para gerar cronograma
        ttk.Button(root, text="Gerar Cronograma Otimizado", command=self.generate).pack(pady=5)

        # Área para exibir cronograma
        self.text_area = tk.Text(root, height=15, width=80)
        self.text_area.pack(pady=10, padx=10)

    def setup_prof_frame(self):
        ttk.Label(self.prof_frame, text="Nome do Professor:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.prof_nome = tk.Entry(self.prof_frame)
        self.prof_nome.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.prof_frame, text="Disponibilidade (ex: Segunda,Terça):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.prof_disp = tk.Entry(self.prof_frame)
        self.prof_disp.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.prof_frame, text="Preferências (ex: Matemática,Segunda):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.prof_pref = tk.Entry(self.prof_frame)
        self.prof_pref.grid(row=2, column=1, padx=5, pady=5)

        ttk.Button(self.prof_frame, text="Adicionar Professor", command=self.add_prof).grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(self.prof_frame, text="Limpar Campos", command=self.clear_prof).grid(row=4, column=0, columnspan=2, pady=5)

    def setup_mat_frame(self):
        ttk.Label(self.mat_frame, text="Nome da Matéria:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.mat_nome = tk.Entry(self.mat_frame)
        self.mat_nome.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.mat_frame, text="Carga Horária (número):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mat_carga = tk.Entry(self.mat_frame)
        self.mat_carga.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(self.mat_frame, text="Adicionar Matéria", command=self.add_mat).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(self.mat_frame, text="Limpar Campos", command=self.clear_mat).grid(row=3, column=0, columnspan=2, pady=5)

    def setup_tur_frame(self):
        ttk.Label(self.tur_frame, text="Nome da Turma:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tur_nome = tk.Entry(self.tur_frame)
        self.tur_nome.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.tur_frame, text="Ano (número):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.tur_ano = tk.Entry(self.tur_frame)
        self.tur_ano.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(self.tur_frame, text="Adicionar Turma", command=self.add_tur).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(self.tur_frame, text="Limpar Campos", command=self.clear_tur).grid(row=3, column=0, columnspan=2, pady=5)

    def setup_data_frame(self):
        self.data_text = tk.Text(self.data_frame, height=15, width=80)
        self.data_text.pack(pady=10, padx=10)
        ttk.Button(self.data_frame, text="Atualizar Lista", command=self.list_data).pack(pady=5)

    def clear_prof(self):
        self.prof_nome.delete(0, tk.END)
        self.prof_disp.delete(0, tk.END)
        self.prof_pref.delete(0, tk.END)

    def clear_mat(self):
        self.mat_nome.delete(0, tk.END)
        self.mat_carga.delete(0, tk.END)

    def clear_tur(self):
        self.tur_nome.delete(0, tk.END)
        self.tur_ano.delete(0, tk.END)

    def add_prof(self):
        nome = self.prof_nome.get().strip()
        disp = self.prof_disp.get().strip()
        pref = self.prof_pref.get().strip()
        if not nome:
            messagebox.showerror("Erro", "O nome do professor é obrigatório!")
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO professores (nome, disponibilidade, preferencias) VALUES (%s, %s, %s)", (nome, disp, pref))
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Professor '{nome}' adicionado!")
            self.clear_prof()
        except Error as e:
            messagebox.showerror("Erro", f"Falha ao adicionar professor: {e}")

    def add_mat(self):
        nome = self.mat_nome.get().strip()
        carga = self.mat_carga.get().strip()
        if not nome:
            messagebox.showerror("Erro", "O nome da matéria é obrigatório!")
            return
        try:
            carga = int(carga)
            if carga <= 0:
                raise ValueError("Carga horária deve ser um número positivo!")
        except ValueError:
            messagebox.showerror("Erro", "Carga horária deve ser um número inteiro positivo!")
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO materias (nome, carga_horaria) VALUES (%s, %s)", (nome, carga))
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Matéria '{nome}' adicionada!")
            self.clear_mat()
        except Error as e:
            messagebox.showerror("Erro", f"Falha ao adicionar matéria: {e}")

    def add_tur(self):
        nome = self.tur_nome.get().strip()
        ano = self.tur_ano.get().strip()
        if not nome:
            messagebox.showerror("Erro", "O nome da turma é obrigatório!")
            return
        try:
            ano = int(ano)
            if ano <= 0:
                raise ValueError("Ano deve ser um número positivo!")
        except ValueError:
            messagebox.showerror("Erro", "Ano deve ser um número inteiro positivo!")
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO turmas (nome, ano) VALUES (%s, %s)", (nome, ano))
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Turma '{nome}' adicionada!")
            self.clear_tur()
        except Error as e:
            messagebox.showerror("Erro", f"Falha ao adicionar turma: {e}")

    def list_data(self):
        self.data_text.delete(1.0, tk.END)
        cursor = self.conn.cursor()

        self.data_text.insert(tk.END, "Professores:\n")
        cursor.execute("SELECT nome, disponibilidade, preferencias FROM professores")
        for nome, disp, pref in cursor.fetchall():
            self.data_text.insert(tk.END, f"- {nome} (Disp: {disp or 'Nenhuma'}, Pref: {pref or 'Nenhuma'})\n")

        self.data_text.insert(tk.END, "\nMatérias:\n")
        cursor.execute("SELECT nome, carga_horaria FROM materias")
        for nome, carga in cursor.fetchall():
            self.data_text.insert(tk.END, f"- {nome} (Carga: {carga}h)\n")

        self.data_text.insert(tk.END, "\nTurmas:\n")
        cursor.execute("SELECT nome, ano FROM turmas")
        for nome, ano in cursor.fetchall():
            self.data_text.insert(tk.END, f"- {nome} (Ano: {ano})\n")

    def generate(self):
        optimize_schedule(self.conn)
        self.display_schedules()

    def display_schedules(self):
        self.text_area.delete(1.0, tk.END)
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT p.nome, m.nome, t.nome, c.dia_semana, c.horario_inicio, c.horario_fim
        FROM cronogramas c
        JOIN professores p ON c.professor_id = p.id
        JOIN materias m ON c.materia_id = m.id
        JOIN turmas t ON c.turma_id = t.id
        ORDER BY p.nome, c.dia_semana, c.horario_inicio
        """)
        results = cursor.fetchall()
        if not results:
            self.text_area.insert(tk.END, "Nenhum cronograma gerado ainda.\n")
            return
        current_prof = ""
        for row in results:
            prof, mat, tur, dia, ini, fim = row
            if prof != current_prof:
                self.text_area.insert(tk.END, f"\nCronograma para {prof}:\n")
                current_prof = prof
            self.text_area.insert(tk.END, f"- {dia}: {mat} para {tur} das {ini} às {fim}\n")

# Execução principal
if __name__ == "__main__":
    conn = create_connection()
    if conn:
        create_tables(conn)
        root = tk.Tk()
        app = SchoolApp(root, conn)
        root.mainloop()
        conn.close()