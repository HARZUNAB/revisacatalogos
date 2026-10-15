import subprocess
import sys
import os
import re
from datetime import datetime

# ==============================================================================
# CONFIGURACIÓN DE RED Y ENTORNOS REMOTOS (CATÁLOGO WEB)
# ==============================================================================
IP_REMOTA = "10.54.217.9"
USUARIO_REMOTO = "sysop"
DIR_REMOTO = "/home/sysop/tmp"
EXE_EVENTQUERY = "/home/sysop/bin/eventquery"

def solicitar(nombre, ejemplo, tipo_dato, obligatorio=False):
    while True:
        prompt = f"🔹 {nombre:<25} (Ej: {ejemplo})"
        prompt += "\t[OBLIGATORIO]: " if obligatorio else "\t[ENTER para omitir]: "
        
        try:
            entrada = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[-] Operación cancelada por el usuario.")
            sys.exit(1)

        if not entrada:
            if obligatorio:
                print(f"   Error: El campo '{nombre}' no puede estar vacío.")
                continue
            return None
        
        # VALIDACIONES
        if tipo_dato == "tiempo_corto":
            if re.match(r"^\d{14}$", entrada):
                try:
                    dt = datetime.strptime(entrada, "%Y%m%d%H%M%S")
                    return dt.strftime("%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    print("   Error: Fecha o hora inválida (ej. mes 13 o día 32).")
            else:
                print("   Error: Use el formato AAAAMMDDHHMMSS (14 dígitos).")
        
        elif tipo_dato == "numero":
            try:
                float(entrada)
                return entrada
            except ValueError:
                print("   Error: Ingrese un valor numérico válido.")
        
        elif tipo_dato == "texto":
            # Sanear la entrada eliminando caracteres peligrosos para SSH
            return re.sub(r"[`$;\"']", "", entrada)


def _normalizar_salida(output):
    """Asegura la extensión .csv en el nombre del archivo de salida."""
    if not output.lower().endswith('.csv'):
        output += '.csv'
    return output


def _construir_args(start, end, opcionales, output):
    """
    Lista de argumentos de eventquery.

    'opcionales' es una lista de (flag, valor); se incluyen solo los que tienen
    valor (los filtros omitidos quedan en None). El archivo de salida va al final.
    """
    args = ["--start-time", start, "--end-time", end]
    for flag, valor in opcionales:
        if valor is not None:
            args.extend([flag, valor])
    args.append(output)
    return args


def _comando_remoto(args_list):
    """Comando que corre en el servidor: asegura el directorio y llama a eventquery."""
    return "mkdir -p %s && cd %s && %s %s" % (
        DIR_REMOTO, DIR_REMOTO, EXE_EVENTQUERY, " ".join(args_list))


def _hay_datos(ruta):
    """True si el archivo existe y no está vacío (0 bytes = sin datos)."""
    return os.path.isfile(ruta) and os.path.getsize(ruta) > 0


def _avisar_sin_datos(archivo_local):
    """Avisa que la ventana no trajo datos y limpia el archivo vacío si quedó."""
    print("\n[-] No hay datos en la ventana solicitada.")
    if os.path.isfile(archivo_local):
        try:
            os.remove(archivo_local)
        except OSError:
            pass


def main():
    # ==============================================================================
    # INTERFAZ DE USUARIO (CAPTURA DE PARÁMETROS)
    # ==============================================================================
    print("\n" + "="*70)
    print("             INGRESO DE PARÁMETROS PARA EL CATÁLOGO WEB")
    print("="*70)

    while True:
        print("Ingrese tiempo en formato: AAAAMMDDHHMMSS")
        start = solicitar("Start Time", "20260501000000", "tiempo_corto", obligatorio=True)
        end   = solicitar("End Time",   "20260507235959", "tiempo_corto", obligatorio=True)
        
        t_start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        t_end   = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
        
        if t_end > t_start:
            break
        else:
            print("\n ❌ ERROR LÓGICO: La fecha de FIN debe ser posterior a la de INICIO.")
            print("   Por favor, ingrese el rango de tiempo nuevamente.\n")

    output = solicitar("Nombre archivo salida", "datos.csv", "texto", obligatorio=True)
    output = _normalizar_salida(output)

    directorio = solicitar("Nombre carpeta imágenes", "analista", "texto", obligatorio=True)

    print("-" * 70)
    min_lat = solicitar("Latitud Mínima", "-38.5", "numero")
    max_lat = solicitar("Latitud Máxima", "-32.0", "numero")
    min_lon = solicitar("Longitud Mínima", "-75.0", "numero")
    max_lon = solicitar("Longitud Máxima", "-69.5", "numero")
    min_dep = solicitar("Profundidad Mínima", "0", "numero")
    max_dep = solicitar("Profundidad Máxima", "150", "numero")
    min_mag = solicitar("Magnitud Mínima", "3.0", "numero")
    max_mag = solicitar("Magnitud Máxima", "9.0", "numero")

    # ==============================================================================
    # CONSTRUCCIÓN DE ARGUMENTOS PARA EVENTQUERY
    # ==============================================================================
    opcionales = [
        ("--min-latitude", min_lat), ("--max-latitude", max_lat),
        ("--min-longitude", min_lon), ("--max-longitude", max_lon),
        ("--min-depth", min_dep), ("--max-depth", max_dep),
        ("--min-magnitude", min_mag), ("--max-magnitude", max_mag)
    ]
    args_list = _construir_args(start, end, opcionales, output)

    # ==============================================================================
    # EJECUCIÓN REMOTA VÍA SSH (USANDO SUBPROCESS)
    # ==============================================================================
    print("\n" + "="*70)
    print(f"[+] Conectando a {USUARIO_REMOTO}@{IP_REMOTA} vía SSH...")
    print("="*70 + "\n")

    # Comando estructurado para asegurar el directorio y correr eventquery
    comando_remoto = _comando_remoto(args_list)

    try:
        # Ejecutamos el SSH compartiendo los flujos estándar (el usuario verá el progreso en vivo)
        subprocess.run(
            ["ssh", f"{USUARIO_REMOTO}@{IP_REMOTA}", f"/bin/bash -c '{comando_remoto}'"],
            check=True
        )
        
        print("\n[+] Consulta finalizada con éxito en el servidor remoto.")
        
        # ==============================================================================
        # TRANSFERENCIA DEL ARCHIVO GENERADO VÍA SCP
        # ==============================================================================
        # Definimos la ruta local donde se está ejecutando el script
        ruta_local_destino = os.getcwd()
        archivo_local = os.path.join(ruta_local_destino, output)
        print(f"[+] Descargando '{output}' hacia la ruta local: {ruta_local_destino}")

        try:
            subprocess.run(
                ["scp", f"{USUARIO_REMOTO}@{IP_REMOTA}:{DIR_REMOTO}/{output}", ruta_local_destino],
                check=True
            )
        except subprocess.CalledProcessError:
            # Si el scp falla porque el remoto no generó el archivo (ventana sin
            # eventos), no es un error del sistema: simplemente no hay datos.
            if not _hay_datos(archivo_local):
                _avisar_sin_datos(archivo_local)
                return
            raise

        # Un archivo de 0 bytes (bajada vacía) tampoco es un resultado válido.
        if not _hay_datos(archivo_local):
            _avisar_sin_datos(archivo_local)
            return

        print("\n" + "="*70)
        print(f" 🌟 [¡ÉXITO!] Proceso completo terminado.")
        print(f"    -> Archivo descargado: {os.path.join(ruta_local_destino, output)}")
        print(f"    -> Carpeta asignada:  {directorio}")
        print("="*70 + "\n")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error crítico durante la ejecución del comando del sistema: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
