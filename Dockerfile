FROM bitnami/jupyter-base-notebook
 
WORKDIR /workspace
USER root

RUN apt-get update -y 
RUN apt-get install -y cifs-utils

RUN pip install scipy
RUN pip install pandas
RUN pip install h5py
RUN pip install matplotlib


RUN touch /credentials.txt
 
RUN mkdir /NAS

EXPOSE 8888

CMD ["jupyter", "notebook", "--port=8888", "--no-browser", "--ip=0.0.0.0", "--allow-root", "--NotebookApp.token='letmein'", "--NotebookApp.password='', --NotebookApp.allow_remote_access=true"]