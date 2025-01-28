from flask import Flask, request, jsonify
import datetime
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Padronização de conexão ao PostgreSQL
DB_PRODUTOS_CONFIG = {
    "dbname": "dbProdutos",
    "user": "seu_usuario",
    "password": "sua_senha",
    "host": "seu_host",
    "port": "5432"
}

DB_VALIDADE_CONFIG = {
    "dbname": "dbValidades",
    "user": "seu_usuario",
    "password": "sua_Senha",
    "host": "seu_host",
    "port": "5432"
}


@app.route('/api/v1/products/<string:codbarras>', methods=['GET'])
def get_product_by_barcode(codbarras):
    try:
        # conecta ao banco dbProdutos
        conn = psycopg2.connect(
            dbname="produtos",
            user="seu_usuario",
            password="sua_senha",
            host="seu_host",
            port="5432"
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Consulta SQL
        cursor.execute("""
            SELECT prod_codbarras, prod_descrpdvs, prod_comp_codigo ,prod_dpto_codigo
            FROM produtos
            WHERE prod_codbarras = %s
        """, (codbarras,))
        
        product = cursor.fetchone()
        conn.close()

        if not product:
            return {"message": "Produto não encontrado"}, 404

        return product, 200

    except Exception as e:
        return {"error": str(e)}, 500
    
# Função para conectar ao banco de dados dbValidades
def connect_dbvalidade():
    return psycopg2.connect(**DB_VALIDADE_CONFIG)


@app.route('/api/departamento/<string:departamento>', methods=['GET'])
def getDepartamento(departamento):
    try:
        # Conectando ao banco de dados flex
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Consulta SQL
        if departamento == 'todos':
            cursor.execute("""
                SELECT id, codbarras, descricao, datadevalidade, quantidade, departamento, loja
                FROM tblancamentos
                WHERE enviado = FALSE
               
            """)      
        else:
            query = "SELECT id, codbarras, descricao, datadevalidade, quantidade, departamento, loja FROM tbLancamentos WHERE enviado = FALSE AND departamento = %s"
            cursor.execute(query, (departamento,))
        
        product = cursor.fetchall()
        conn.close()

        if not product:
            return {"message": "Produtos não encontrados"}, 404

        return product, 200

    except Exception as e:
        return {"error": str(e)}, 500

# Rota para lançar o produto no dbValidades
@app.route('/api/v1/lancar_produto', methods=['POST'])
def lancar_produto():
    data = request.get_json()

    required_fields = ["codbarras", "descricao",  "departamento", "datadevalidade", "quantidade","loja"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo {field} é obrigatório."}), 400

    codbarras = data["codbarras"]
    descricao = data["descricao"]
    
    departamento = data["departamento"]
    datadevalidade = data["datadevalidade"]
    quantidade = data["quantidade"]
    loja = data["loja"]

    try:
        conn_dbvalidade = connect_dbvalidade()
        cursor = conn_dbvalidade.cursor()

        cursor.execute(
            """
            INSERT INTO tbLancamentos (codbarras, descricao, departamento, datadevalidade, quantidade, loja, enviado)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE)
            """,
            (codbarras, descricao,  departamento, datadevalidade, quantidade, loja)
        )

        conn_dbvalidade.commit()
        conn_dbvalidade.close()

        return jsonify({"success": "Produto lançado com sucesso."}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao lançar produto: {str(e)}"}), 500

@app.route('/api/v1/lancar_peso', methods=['POST'])
def lancar_peso():
    data = request.get_json()

    required_fields = ["codbarras", "descricao", "quantidade","loja"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo {field} é obrigatório."}), 400

    codbarras = data["codbarras"]
    descricao = data["descricao"]
    quantidade = data["quantidade"]
    loja = data["loja"]

    try:
        conn_dbvalidade = connect_dbvalidade()
        cursor = conn_dbvalidade.cursor()

        cursor.execute(
            """
            INSERT INTO pesotemp (codbarras, descricao, peso, unidade)
            VALUES (%s, %s, %s, %s)
            """,
            (codbarras, descricao, quantidade, loja)
        )

        conn_dbvalidade.commit()
        conn_dbvalidade.close()

        return jsonify({"success": "Produto lançado com sucesso."}), 201

    except Exception as e:
        return jsonify({"error": f"Erro ao lançar produto: {str(e)}"}), 500

@app.route('/api/v1/login', methods=['POST'])
def login():
    conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
    data = request.get_json()
    login = data.get("login")
    senha = data.get("senha")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT senha, tipo FROM usuarios WHERE login = %s", (login,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"error": "Usuário não encontrado"}), 401

            senha_hash, tipo = user

            # Verifica a senha
            if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
                return jsonify({"success": "Login efetuado", "tipo": tipo})
            else:
                return jsonify({"error": "Senha incorreta"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# concluir e atualziar abaixo

@app.route('/api/v1/atualizar_produto/<int:id>-<string:preco>', methods=['PUT'])
def atualizar_produto(id, preco):
    
    preco = "R$ "+preco
    try:
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE tbLancamentos
                SET enviado = TRUE, novopreco = %s
                WHERE id = %s AND enviado = FALSE
            """, (preco,id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Produto não encontrado ou já atualizado"}), 404
            conn.commit()
            return jsonify({"success": "Produto movido para ATUALIZADOS"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/v1/atualizar_preco/<int:id>-<string:preco>', methods=['PUT'])
def atualizar_preco(id,preco):
    preco="R$ "+preco
    try:
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE tbLancamentos
                SET novopreco = %s
                WHERE id = %s 
            """, (preco,id,))
            # AND enviado = FALSE
            if cursor.rowcount == 0:
                return jsonify({"error": "Produto não encontrado ou já atualizado"}), 404
            conn.commit()
            return jsonify({"success": "Produto movido para ATUALIZADOS"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/v1/corrigir/<int:id>', methods=['PUT'])
def corrigir_produto(id):
    # dataatual="'"+str(datetime.date.today())+"'"
    try:
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE tbLancamentos
                SET concluido = FALSE
                WHERE id = %s
            """, (id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Produto não encontrado ou não concluído"}), 404
            conn.commit()
            return jsonify({"success": "Produto movido para ATUALIZADOS"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/corrigiratt/<int:id>', methods=['PUT'])
def corrigir_produtoatt(id):
    
    try:
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE tbLancamentos
                SET enviado = FALSE
                WHERE id = %s
            """, (id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Produto não encontrado ou não concluído"}), 404
            conn.commit()
            return jsonify({"success": "Produto movido para PENDENTES"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/concluir_produto/<int:id>', methods=['PUT'])
def concluir_produto(id):
    dataatual="'"+str(datetime.date.today())+"'"
    try:
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE tbLancamentos
                SET concluido = TRUE, datalancamento = %s
                WHERE id = %s AND enviado = TRUE AND concluido = FALSE
            """, (dataatual,id,))
            if cursor.rowcount == 0:
                return jsonify({"error": "Produto não encontrado ou já concluído"}), 404
            conn.commit()
            return jsonify({"success": "Produto movido para CONCLUÍDOS"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#if (tabName === "pendentes") url = `${API_URL}/produtos?enviado=false`;
#else if (tabName === "atualizados") url = `${API_URL}/produtos?enviado=true&concluido=false`;


# endpoint para puxar produtos nao enviados
@app.route('/api/v1/produtos/false', methods=['GET'])
def get_product_by_enviado_false():
    try:
        # Conectando ao banco de dados flex
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="Jesusestavoltando",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Consulta SQL
        cursor.execute("""
            SELECT id, codbarras, descricao, datadevalidade, quantidade, departamento, loja
            FROM tblancamentos
            WHERE enviado = FALSE
        """)
        
        product = cursor.fetchall()
        conn.close()

        if not product:
            return {"message": "Produto não encontrado"}, 404

        return product, 200

    except Exception as e:
        return {"error": str(e)}, 500

# endpoint para puxcar produtos enviados, porem nao concluidos
@app.route('/api/v1/produtoss/true', methods=['GET'])
def get_product_by_enviado_true():
    try:
        # Conectando ao banco de dados flex
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Consulta SQL
        cursor.execute("""
            SELECT id, codbarras, descricao, datadevalidade, quantidade, novopreco, loja
            FROM tblancamentos
            WHERE enviado = TRUE and concluido = FALSE
        """)
        
        product = cursor.fetchall()
        conn.close()

        if not product:
            return {"message": "Produto não encontrado"}, 404

        return product, 200

    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/v1/concluidos', methods=['GET'])
def get_product_by_concluidos():
    dataatual="'"+str(datetime.date.today())+"'"
    try:
        # Conectando ao banco de dados flex
        conn = psycopg2.connect(
            dbname="dbValidades",
            user="seu_usuario",
            password="sua_senha",
            host="127.0.0.1",
            port="5432"
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Consulta SQL
        cursor.execute("""
            SELECT id, codbarras, descricao, datadevalidade, quantidade, novopreco, loja
            FROM tblancamentos
            WHERE enviado = TRUE and concluido = TRUE and datalancamento = %s
        """, (dataatual,))
        
        product = cursor.fetchall()
        conn.close()

        if not product:
            return {"message": "Produto não encontrado"}, 404

        return product, 200

    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=True) # permite acesso de qualquer host na porta 9000

