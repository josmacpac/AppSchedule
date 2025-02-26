from flask import Flask, render_template, request, redirect, url_for 
import os
import database as db
import schedule as s
from flask import flash
import pandas as pd

template_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
template_dir = os.path.join(template_dir, 'src', 'templates')


app = Flask(__name__, template_folder= template_dir)
app.secret_key =  'mi_clave_secreta'

##Rutas de la aplcacion

@app.route('/login')
def login():
    return render_template('index.html', content=render_template('login.html'))

@app.route('/')
def home():
    return render_template('index.html', content=render_template('dashboard.html'))



@app.route('/colaboradores')
def mostrar_colaboradores ():

    cursor = db.database.cursor()
    cursor.execute('SELECT * FROM empleados')
    myresult = cursor.fetchall()
    #convertir datos a diccionario
    insertObject = []
    columnNames = [column[0] for column in cursor.description]
    for record in myresult:
        insertObject.append(dict(zip(columnNames, record)))
    cursor.close()   

    cursor = db.database.cursor()
    cursor.execute('SELECT * FROM disponibilidad')
    resultado = cursor.fetchall()
    #convertir datos a diccionario
    disponibilidad = []
    columnNames = [column[0] for column in cursor.description]
    for r in resultado:
        disponibilidad.append(dict(zip(columnNames, r)))
    cursor.close()   

    ##print(disponibilidad)
 


    return render_template('index.html', content=render_template('colaboradores.html',data=insertObject, disponibilidad = disponibilidad))

def repetidos(diccionario):
    valores = list(diccionario.values())
    return len(valores) != len(set(valores))

@app.route('/new_schedule', methods=['POST'])
def new_schedule():

    try:
        ##Obtener dats del formulario 
        date = request.form['date']
        rate_tm = request.form['porcentajeTurnoMat']
        prioridad_dia = {dia: request.form.get(f"turno_{dia}") for dia in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]}
        
        if not date or not rate_tm:
            flash("Error: Fecha y porcentaje del turno matutino son obligatorios.", "error")
            return redirect(url_for('nuevo_horario'))
        if repetidos(prioridad_dia) == True:
            flash("Hay valores repetidos en los dias de la semana, verifique", "warning")
            return redirect(url_for('nuevo_horario'))
        else:
            horario = s.new_schedule(date, rate_tm, prioridad_dia)
            print("generando horario...")
            df = pd.DataFrame(horario)
            df_pivot = df.pivot(index="id_empleado", columns="id_dia", values="turno")
            # Para que se vea más ordenado
            df_pivot = df_pivot.reset_index()
            print(df_pivot)

            table_html = df_pivot.to_html(classes='table table-stripped', index=False)

            return render_template('horario_generado.html', table=table_html, data= date)

    except Exception as e:
        flash(f"Error inesperado: {str(e)}", "error")
        
    
    

## Ruta para guardar un nuevo registro 
@app.route('/user', methods=['POST'])
def addUser():
    id_empleado = request.form['id_empleado']
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    tipo_turno = request.form['tipo_turno']

    ## Falta agregar validacion de datos en tipo de turno, id ,etc
    # validar que el id no este repetido

    if id_empleado and nombre and apellido and tipo_turno:
        cursor = db.database.cursor()
        sql = "INSERT INTO empleados (id_empleado, nombre, apellido, tipo_turno) VALUES(%s, %s, %s, %s)"
        data = (id_empleado, nombre, apellido, tipo_turno)
        cursor.execute(sql, data)
        db.database.commit()
    return redirect(url_for('mostrar_colaboradores'))

 ## Ruta para eliminar registros   
## No se puede eliminar un registro que esta en otra tabla como disponibilidad u Horarios

@app.route('/delete/<string:id>')
def delete(id):
        cursor =db.database.cursor()
        sql = "DELETE FROM empleados WHERE id_empleado =%s"
        data = (id,)
        cursor.execute(sql, data)
        db.database.commit()
        return redirect(url_for('mostrar_colaboradores'))

        ## Mandar mensaje d error o alerta si el usuario tiene registros en otras DB
        ## Borrar datos en todas las tablas 

## Ruta para editar registros

@app.route('/nuevo_horario')
def nuevo_horario():
    return render_template('index.html', content=render_template('nuevo_horario.html'))    

@app.route('/edit/<string:id>', methods=['POST'])
def edit(id):
    id_empleado = request.form['id_empleado']
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    tipo_turno = request.form['tipo_turno']

     # Reconstruir la disponibilidad desde request.form

    disponibilidad = {}
    for key, value in request.form.items():
        if key.startswith('disponibilidad'):
            _, dia, turno = key.split('[')
            dia = dia.rstrip(']')
            turno = turno.rstrip(']')
            if dia not in disponibilidad:
                disponibilidad[dia] = {}
            disponibilidad[dia][turno] = value
    
    
    
   
    if nombre and apellido and tipo_turno:    
        cursor =db.database.cursor()
        sql = "UPDATE empleados SET nombre=%s, apellido=%s, tipo_turno=%s WHERE id_empleado =%s"
        data = (nombre, apellido, tipo_turno, id_empleado)
        cursor.execute(sql, data)

        # Limpia la disponibilidad actual en la base de datos
        cursor.execute(f"DELETE FROM disponibilidad WHERE id_empleado = {id_empleado}")
        
        # Inserta los nuevos datos de disponibilidad
        for dia, horarios in disponibilidad.items():
            sql = """
                INSERT INTO disponibilidad (
                    id_empleado, id_dia, apertura_1, apertura_2, apertura_3, 
                    intermedio_1, intermedio_2, intermedio_3, cierre_1, cierre_2, 
                    desc_mat, vacaciones, desc_ves
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            data = (
                id_empleado, dia,
                horarios.get('apertura_1', '0'), horarios.get('apertura_2', '0'), horarios.get('apertura_3', '0'),
                horarios.get('intermedio_1', '0'), horarios.get('intermedio_2', '0'), horarios.get('intermedio_3', '0'),
                horarios.get('cierre_1', '0'), horarios.get('cierre_2', '0'),
                horarios.get('desc_mat', '0'), horarios.get('vacaciones', '0'), horarios.get('desc_ves', '0')
            )
            cursor.execute(sql, data)
       
        print('disponibilidad actualziada!!')
        flash('disponibilidad actualizada correctamentr!!')
        
        
    
        db.database.commit()
    return redirect(url_for('mostrar_colaboradores'))









if __name__== '__main__':
    app.run(debug=True, port=3800)