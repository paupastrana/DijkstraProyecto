import math, re
from typing import Dict, List, Tuple
from flask import Flask, jsonify, render_template, request
import osmnx as ox
import networkx as nx
ox.settings.log_console=True
ox.settings.use_cache=True



zonas_oax=["Oaxaca de Juárez, Oaxaca, Mexico","Santa Cruz Xoxocotlán, Oaxaca, Mexico","San Raymundo Jalpan, Oaxaca, Mexico",]#escribimos las zonas que queremos para el mapa
tipo_calles="drive"#definimos que son calles en las que se puede manejar
velocidad_defecto= 20.0  #para las calles que notienen una velocidad asignada

def dijkstra2(grafo, inicial, final): #funcion para encontrar la distancia mas corta(dikstra)
    distancia = {nodo:float('inf') for nodo in grafo}#inicializamos todas las distancias como infinito
    distancia[inicial]=0#la distancia del nodo inicial a si mismo es 0

    nodos_no_visitados=list(grafo.keys())#creamos la lista de nodos no visitados
    lista_predecesores={nodo: None for nodo in grafo}#creamos la lista de predecesores

    while nodos_no_visitados:#mientras la lista no este vacia
        nodo_actual=min(nodos_no_visitados,key=lambda nodo:distancia[nodo])

        if nodo_actual==final:#si ya llegamos al destino terminamos
            # print(f"Ruta óptima encontrada")
            break

        nodos_no_visitados.remove(nodo_actual)#se elimina el nodo actual de la lista de no visitados
        if distancia[nodo_actual]==float('inf'):#si la distancia es infinito significa que no se puede llegar a ese nodo
            break

        for adyacente, costo in grafo[nodo_actual].items():#recorremos los nodos adyacentes
            distancia_nueva=distancia[nodo_actual]+costo#ña distancia nueva es la suma de la distancia actual mas el costo para llegar al adyacente
            if (distancia_nueva<distancia[adyacente]):#si la distancia nueva es menor a la que ya teniamos la actualizamos
                distancia[adyacente] = distancia_nueva
                lista_predecesores[adyacente] = nodo_actual

    return distancia, lista_predecesores#regresamos las distancias y los predecesores

def convertir_a_kmh(velmax): #convertir de mph a kph
    if velmax is None:
        return math.nan #representa un un numero no real como un none en numero
    val = None
    s=str(velmax)#convierte la velocidad maxima a string
    m=re.search(r"(\d+(\.\d+)?)",s)#encuentra el primer numero en el string lo guarda en m
    if m:
        val=float(m.group(1))#convierte el numero encontrado a float
        if "mph" in s.lower():#si es que esta en mph lo converitmos a km/h
            val*=1.60934
    if val is not None and val:#si hay valor lo regresamos
        return val
    else:#si no hay valor regresas nan
        return math.nan        
    
def convertir_a_ms(kph):#convierte de k/h a m/s
    return(kph*1000.0)/3600.0

def calcular_tiempo(G,veldef):#crea un diccionario que tiene el tiempo entre cada par de nodos
    tiempos:Dict[int,Dict[int, float]]={}
    for u,v,key,data in G.edges(keys=True,data=True):
        length_m=float(data.get("length"))#obtenemos la longitud de cada arista
        kph=convertir_a_kmh(data.get("maxspeed"))#convertimos la velocida a kph
        if math.isnan(kph) or kph<=0:#si noetiene velocidad maxima usamos la que definimos
            kph=veldef
        mps=convertir_a_ms(kph)#convertimos a m/s 
        seg=length_m/mps#sacamos el tiempo
        data["tiempo"]=seg#guardamos el tiempo como un nuevo atributo
        if u not in tiempos:#creamos el diccionario de cada nodo origen
            tiempos[u]={}
        if (v not in tiempos[u] or seg<tiempos[u][v]):#inbresamos el valor si es que no esta o si encontramos un tiempo mas corto
            tiempos[u][v]=seg
    for n in G.nodes:
        tiempos.setdefault(n,{})#metemos todos los nodos restantes al diccionario de tiempos con valor vacio
    return G,tiempos #regresamos el grafo y el diccionario de tiempos

def encontrar_ruta(predecesores, inicial, final):
    ruta=[]#creamos la ruta vacia
    nodo_actual=final#empezamos desde el final
    while nodo_actual is not None:#mientras no estemos en el inicio
        ruta.append(nodo_actual)#metemos el nodo a la lista
        nodo_actual=predecesores.get(nodo_actual, None) #buscamos el predecesor del nodo actual
    ruta.reverse()#lo acomodamos
    if (ruta and ruta[0]==inicial):#si encontramos una ruta correcta la enviamos
        return ruta
    else:#si no llegamos al inciio regresamos lista vacia
        return []

def sumar_atributo(G,ruta,atributo):#va sumando los atributos en la ruta
    total = 0.0#empezamos con 0
    for i in range(len(ruta)-1):#recorremos el tamaño de la ruta
        u,v=ruta[i],ruta[i+1]#obtenemos cada nodo origen y destino
        valores=[]#creamos una lista para guardar los valores de cada arista entre u y v
        for a, datosa in G[u][v].items():#recorremos todas las aristas entre u y v
            if atributo in datosa:
                valor=float(datosa[atributo])#obtenemos y convertimos el valor
            else:
                valor=float("inf")#si no existe el atributo    
            valores.append(valor)  # guardamos el valor en la lista
        if len(valores)>0:
            total+=min(valores)#agarra el valor mas pequeño y lo suma
    return total

def encontrar_coordenadas(G, ruta):#encuentra las coordenadas de cada nodo en la ruta
    coord=[]#creamos lista vacia
    for nodo in ruta:
        lat=float(G.nodes[nodo]["y"])#guardamos la latitud
        lon=float(G.nodes[nodo]["x"])#guardamos la longitud
        coord.append([lat, lon])#metemos la cordenada a la lista
    return coord    



GRAFO=ox.graph_from_place(zonas_oax,network_type=tipo_calles,simplify=True)#descargamos el grafo de las zonas definidas
GRAFO,ADY=calcular_tiempo(GRAFO,velocidad_defecto)

#encontramos el centro para poder centrar el mapa al mostrarlo
LAT_CENTRO=sum(d["y"] for _, d in GRAFO.nodes(data=True))/GRAFO.number_of_nodes()
LON_CENTRO=sum(d["x"] for _, d in GRAFO.nodes(data=True))/GRAFO.number_of_nodes()


aplicacion=Flask(__name__)#creamos una aplicacion flask
def mostrar_mapa():
    return render_template("Paulina_ExamenDijkstra.html", lat=str(LAT_CENTRO), lon=str(LON_CENTRO))#funcion para mostrar el html cambiando las variables
aplicacion.add_url_rule("/","mostrar_mapa", mostrar_mapa)#cuando el usuario entre correra la funcion mostrar mapa

def calcular_ruta():
    #leer coordenadas del front
    latori=float(request.args.get("lat_o"))
    lonori=float(request.args.get("lon_o"))
    latdes=float(request.args.get("lat_d"))
    londes=float(request.args.get("lon_d"))

    nodo_o=ox.nearest_nodes(GRAFO,lonori,latori)#obtener el nodo mas cercano a las coordenadas del origen
    nodo_d=ox.nearest_nodes(GRAFO,londes,latdes)#obtener el nodo mas cercano a las coordenadas del destino
    distancias,predecesores=dijkstra2(ADY,nodo_o,nodo_d)#usamos la funcion de dikstra para encontrar la ruta mas corta
    ruta_nodos=encontrar_ruta(predecesores,nodo_o,nodo_d)#encontramos la ruta entre ambos nodos

    coords=encontrar_coordenadas(GRAFO,ruta_nodos)#convertimos la ruta de nodos a coordenadas
    distancia_m=sumar_atributo(GRAFO,ruta_nodos,"length")#sumamos las distancias entre los nodos de la ruta
    tiempo_s=sumar_atributo(GRAFO,ruta_nodos,"tiempo")#sumamos los tiempos entre los nodos de la ruta

    return jsonify({
        "coords":coords,                
        "distancia_m":float(distancia_m),
        "tiempo_s":float(tiempo_s)
    })

aplicacion.add_url_rule("/ruta","calcular_ruta",calcular_ruta)#despues de marcar el destino se manda a llamar esta funcion

if __name__=="__main__":
    aplicacion.run(debug=True)#inciia el servidor web de flash



#PARA INICIALIZAR EL PROYECTO : python Paulina_ExamenDijkstra.py
#URL EN NAVEGADOR:  http://127.0.0.1:5000  
