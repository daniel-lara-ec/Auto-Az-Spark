#!/bin/bash

# --- VARIABLES ---
HADOOP_VERSION="3.3.6"
HADOOP_URL="https://git.alephsub0.org/recursos/hadoop-3.3.6.tar.gz"
HADOOP_DIR="/usr/local/hadoop"
JAVA_HOME_PATH="/usr/lib/jvm/java-11-openjdk-amd64" # Ajusta si usas otra versión
USER={{{USUARIO}}}
# --- FUNCIONES ---

# Función para verificar si el comando tuvo éxito
check_success() {
  if [ $? -ne 0 ]; then
    echo "Error: $1"
    exit 1
  fi
}

sudo rm -rf $HADOOP_DIR

# 1. Actualizar el sistema e instalar dependencias
echo "Actualizando el sistema"
sudo apt-get update
sudo apt-get upgrade -y

# --- Instalación Pip
sudo apt-get install -y python3-pip
check_success "No se pudo instalar Pip."

pip3 install python-dotenv
check_success "No se pudo instalar python-dotenv."

pip3 install pandas
check_success "No se pudo instalar pandas."

# --- Instalación Wget
sudo apt-get install -y wget
check_success "No se pudo instalar Wget."

# --- Instalacion rsync
sudo apt-get install -y rsync
check_success "No se pudo instalar rsync."

# --- Instalacion Java 11 --
sudo apt-get install -y openjdk-11-jdk
check_success "No se pudo instalar Java 11."

# --- Verificamos la versión de java
java -version

# --- SCRIPT PRINCIPAL ---

echo "--- Iniciando la instalación automática de Hadoop ---"

# 3. Descargar y extraer Hadoop
echo "Descargando Hadoop..."
wget -P /tmp $HADOOP_URL
check_success "No se pudo descargar Hadoop."

echo "Extrayendo Hadoop y moviéndolo a /usr/local..."
sudo tar -xzf /tmp/hadoop-$HADOOP_VERSION.tar.gz -C /usr/local/
check_success "No se pudo extraer Hadoop."
sudo mv /usr/local/hadoop-$HADOOP_VERSION $HADOOP_DIR
check_success "No se pudo mover la carpeta de Hadoop."

# 5. Configurar variables de entorno
echo "Configurando variables de entorno"
echo "export HADOOP_HOME=$HADOOP_DIR" >> /home/$USER/.bashrc
echo "export JAVA_HOME=$JAVA_HOME_PATH" >> /home/$USER/.bashrc
echo "export HADOOP_CONF_DIR=\$HADOOP_HOME/etc/hadoop" >> /home/$USER/.bashrc
echo "export PATH=\$PATH:\$HADOOP_HOME/sbin:\$HADOOP_HOME/bin" >> /home/$USER/.bashrc



# 7. Configurar archivos principales de Hadoop
echo "Configurando los archivos de configuración de Hadoop..."
# Core-site.xml
sudo tee $HADOOP_DIR/etc/hadoop/core-site.xml > /dev/null <<EOF
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
</configuration>
EOF
check_success "No se pudo configurar core-site.xml."

# Hdfs-site.xml
sudo tee $HADOOP_DIR/etc/hadoop/hdfs-site.xml > /dev/null <<EOF
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
</configuration>
EOF
check_success "No se pudo configurar hdfs-site.xml."

# Mapred-site.xml
sudo tee $HADOOP_DIR/etc/hadoop/mapred-site.xml > /dev/null <<EOF
<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
</configuration>
EOF
check_success "No se pudo configurar mapred-site.xml."

# Yarn-site.xml
sudo tee $HADOOP_DIR/etc/hadoop/yarn-site.xml > /dev/null <<EOF
<configuration>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
    <property>
        <name>yarn.nodemanager.aux-services.mapreduce.shuffle.class</name>
        <value>org.apache.hadoop.mapred.ShuffleHandler</value>
    </property>
</configuration>
EOF
check_success "No se pudo configurar yarn-site.xml."

source /home/$USER/.bashrc

# --- Finalizando la instalación ---
echo "Instalación de Hadoop completada."