FROM continuumio/miniconda3:latest

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/opt/conda/envs/gsp_api/bin:$PATH API_PREFIX=/api

RUN mkdir /var/uwsgi
RUN apt-get update -qq && apt-get install -yqq supervisor vim

COPY environment.yaml ./startup.sh ./

RUN conda config --set channel_priority strict && \
    conda config --add channels conda-forge && \
    conda env create -f environment.yaml && \
    echo "conda activate app-env" >> ~/.bashrc

RUN mkdir -p /mnt/output/forecasts && \
    mkdir -p /mnt/output/era-interim && \
    mkdir -p /mnt/output/era-5 && \
    mkdir -p /mnt/output/forecast-records

# Copy API code
COPY app /app
COPY ./supervisord.conf /etc/supervisor/conf.d/uwsgi.conf

# startup.sh is a helper script
RUN chmod +x /startup.sh

# Expose the port that is to be used when calling your API
EXPOSE 80
HEALTHCHECK --interval=1m --timeout=3s --start-period=20s \
  CMD curl -f http://localhost/ || exit 1
ENTRYPOINT [ "/startup.sh" ]