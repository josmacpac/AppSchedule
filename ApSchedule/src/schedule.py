import database as db
from  itertools import cycle
import os
from tabulate import tabulate
from datetime import datetime, timedelta
from flask import flash
import pandas as pd
import copy

Dict_settings = {
    "date" : None,
    "previous_date" : None,
    "rate_tm": None,
    "rate_tv": None,
    "mon" : 0,
    "tue" : 0,
    "wed" : 0,
    "thr" : 0,
    "fri" : 0,
    "sat" : 0,
    "sun" : 0
}
Dict_schedule = []

Dict_dias = {}
dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]


def listar_disponibilidad():
    cursor = db.database.cursor(dictionary= True)
    my_result = []
    try:
        cursor.execute('SELECT * FROM disponibilidad')
        my_result = cursor.fetchall()
        
    except Exception as e:
        print(f'Error en la consulta: {e}')    
    finally:   
        cursor.close()   
    return my_result

def listar_empleados():
    cursor = db.database.cursor()
    try:
        cursor.execute('SELECT * FROM empleados')
        my_result = cursor.fetchall()
        #print(my_result)
    except:
        print('Error en la consulta')       
    cursor.close()   

    tipo_turno = {}
    for record in my_result:
        key = record[-1]  # Último elemento de la tupla
        tipo_turno[key] = tipo_turno.get(key, 0) + 1

    total_empleados = len(my_result)    

    return my_result, tipo_turno, total_empleados

def calcular_fecha(fecha_str, formato="%Y-%m-%d",):
    dia = (datetime.strptime(fecha_str, formato)).weekday()

    if dia != 0:
        flash("La fecha ingresada no es Lunes, intenta nuevamente ", "error")
        
    else:
        fecha_actual = datetime.strptime(fecha_str, formato)
        fecha_anterior = fecha_actual - timedelta(weeks=1)
        fecha_anterior = fecha_anterior.strftime(formato)
        Dict_settings.update(date= fecha_str, previous_date= fecha_anterior)

        flash("Generando Horario", "success")
        
    
    return fecha_actual, fecha_anterior
        
def calcular_turnos(rate_tm, prioridad_dia):
    rate_tm = int(rate_tm)/100
    rate_tv = (1-rate_tm)  
    
    Dict_settings.update(rate_tm = rate_tm, rate_tv= rate_tv, mon = prioridad_dia.get("Lunes"), tue = prioridad_dia.get("Martes"), wed = prioridad_dia.get("Miercoles"), thr = prioridad_dia.get("Jueves"), fri = prioridad_dia.get("Viernes"), sat = prioridad_dia.get("Sabado"), sun = prioridad_dia.get("Domingo"))

def repartir_descansos(total_empleados, prioridad_dia):
   
   contador = 0
   #print(prioridad_dia)
   dict_ordenado = dict(sorted(prioridad_dia.items(), key=lambda item: item[1])) #ordenar diccionario en base a sus valores
      
   for clave in dict_ordenado:
        dict_ordenado[clave]=0


            ## se utiliza la libreria itertools para iterar el diccionario n veces
   for d in cycle(dict_ordenado):
      dict_ordenado[d] += 1
      contador += 1
  
      if contador == total_empleados: 
        break   
   #print(dict_ordenado)
    # Reordenar según el orden natural de la semana
   dict_reordenado = {dia: dict_ordenado[dia] for dia in dias_semana if dia in dict_ordenado}
   
   return dict_reordenado     

def calc_empleados_turno(total_empleados, prioridad_dia):
    
    #la funcion recibe el total de empleados, % de cada turno, prioridad por dia y devuelve un diccionario 
    #con los dias de la semana y la cantidad de empleados por turno
    listaTurnos = []
    num = total_empleados
    settings = Dict_settings
    emp_tm = round(total_empleados * settings.get("rate_tm"))
    emp_tv = num - emp_tm

    print("total empleados: ", num,"turno matutino: ", emp_tm, "turno vespertino: ",emp_tv)

    descansos_mat = repartir_descansos(emp_tm, prioridad_dia)
    descansos_ves = repartir_descansos(emp_tv, prioridad_dia)

    for dia in dias_semana:
        apertura_1 = round((emp_tm-descansos_mat.get(dia))*0.3) ##establer minimos 
        apertura_2 = round((emp_tm- descansos_mat.get(dia)-apertura_1)*0.3)
        apertura_3 = emp_tm- descansos_mat.get(dia)-apertura_1-apertura_2
        intermedio_1 = emp_tm- descansos_mat.get(dia)-apertura_1-apertura_2-apertura_3
        
        cierre_2 = round((emp_tv-descansos_ves.get(dia))*0.3)
        cierre_1 = round((emp_tv- descansos_ves.get(dia)-cierre_2)*0.3)
        intermedio_3 = emp_tv- descansos_ves.get(dia)-cierre_2-cierre_1
        intermedio_2 = emp_tv- descansos_ves.get(dia)-cierre_2-cierre_1 - intermedio_3

        dict_turnos = {
        "id_dia": dia,
        "apertura_1": apertura_1,
        "apertura_2": apertura_2,
        "apertura_3": apertura_3,
        "intermedio_1": intermedio_1,
        "intermedio_2": intermedio_2,
        "intermedio_3": intermedio_3,
        "cierre_1": cierre_1,
        "cierre_2": cierre_2,
        "desc_mat": descansos_mat.get(dia),
        "desc_ves": descansos_ves.get(dia)}

        listaTurnos.append(dict_turnos)

    return listaTurnos, emp_tm, emp_tv

def asignacion_horario(lista, n, tipo, t, dia):
    n= n
    empleados_disponibles= lista
    tipo = tipo
    contador = t
    dia=dia
    
    while contador > 0 and empleados_disponibles:
        #print(f"asignando empleado:  ", contador)
        for i, e in enumerate(empleados_disponibles):
            if e[3] in ['ft', 'rot']:  # Unificar condiciones
                registro = {"id_empleado": e[0], "id_dia": dia, "turno": tipo}
                Dict_schedule.append(registro)
                empleados_disponibles.pop(i)  # Remover el empleado asignado
                break  # Salir del bucle for una vez asignado un empleado
        contador-=1
        
    

    
def distribuir_empleados(disponibilidad, listado, listaTurnos):
    
    
    tipos_turno = ["cierre_2", "cierre_1", "apertura_1", "apertura_2", "intermedio_3", "apertura_3", "intermedio_2",  "intermedio_1", "desc_mat", "desc_ves" ]
    
    
    for l in listaTurnos:
        dia = l.get("id_dia")

        # Crear una nueva copia de la lista de empleados para cada día
        empleados_ordenados = sorted(listado, key=lambda x: x[3] != 'ft') #ordenar el listado para itear primero los valores "ft"
        empleados_copy = copy.deepcopy(empleados_ordenados)
        print(f"\nProcesando día {dia}, empleados disponibles: {len(empleados_copy)}")
        for t in tipos_turno:
            asignacion_horario(empleados_copy, len(empleados_copy), t, l.get(t, 0), dia)
            
    return Dict_schedule 
            


def new_schedule(date, rate_tm, prioridad_dia):
    fecha_actual, fecha_anterior=calcular_fecha(date) ## obtener fecha actual de formulario y calcular feccha anteriro
    calcular_turnos(rate_tm, prioridad_dia) # obtener ratng por dia del formulario y lo guarda en el diccionario correspondiente
    listado, tipo_turno, total_empleados = listar_empleados() #consulta a DB para obtener cantidad de empleados, tipo de turno 
    listaTurnos, emp_tm, emp_tv =  calc_empleados_turno(total_empleados, prioridad_dia)
    disponibilidad = listar_disponibilidad()

    horario = distribuir_empleados(disponibilidad, listado, listaTurnos)    

    
    
    print("fecha horario: ", fecha_actual, "fecha horario anterior: ",fecha_anterior)
    print(tabulate(listaTurnos, headers="keys"))
    
    #print(horario)

    

    return horario
    
    

    
    
    


    

    



    
    
    
    
    




