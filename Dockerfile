FROM python:3.11-slim
RUN apt update && apt install -y nmap masscan net-tools python3-pip
COPY ./src/requirements.txt ./
RUN pip3 install -r requirements.txt
COPY ./src/ /setezor/
WORKDIR /setezor/
EXPOSE 16661
VOLUME ./projects:/setezor/projects
VOLUME ./logs:/setezor/logs
ENTRYPOINT ["python3", "./setezor.py"]
