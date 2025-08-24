#!/bin/bash

# --- VARIABLES ---
SPARK_VERSION="3.5.4"
SPARK_URL="https://git.alephsub0.org/recursos/spark-3.5.4-bin-hadoop3.tgz"
USER={{{USUARIO}}}
# --- FUNCIONES ---

# Función para verificar si el comando tuvo éxito
check_success() {
  if [ $? -ne 0 ]; then
    echo "Error: $1"
    exit 1
  fi
}


# --- Descargamos spark
echo "Descargando Spark..."
wget -P /tmp $SPARK_URL
check_success "No se pudo descargar Spark."

echo "Extrayendo Spark y moviéndolo a /opt..."
sudo tar -xzf /tmp/spark-3.5.4-bin-hadoop3.tgz -C /opt/
check_success "No se pudo extraer Spark."
sudo mv /opt/spark-3.5.4-bin-hadoop3 /opt/spark

# --- Variables de entorno
echo "export SPARK_HOME=/opt/spark" >> /home/$USER/.bashrc
echo "export PATH=\$SPARK_HOME/bin:\$SPARK_HOME/sbin:\$PATH" >> /home/$USER/.bashrc
echo "export YARN_CONF_DIR=\$HADOOP_HOME/etc/hadoop" >> /home/$USER/.bashrc

source /home/$USER/.bashrc

# --- Configuramos spark-env.sh
sudo tee  /opt/spark/conf/spark-env.sh > /dev/null <<EOL
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
{{{LINEA_CONFIG_1}}}
{{{LINEA_CONFIG_2}}}
{{{LINEA_CONFIG_3}}}
EOL

echo "Configuración de Spark completada."