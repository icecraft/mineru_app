## Installation


```bash
pip install mineru_app
```

or using docker 

```bash
docker pull registry.cn-hangzhou.aliyuncs.com/data_proc/mineru_app:v0.0.10
```

## Start

```bash
export MINERU_API_KEY=your_api_key
mineru_app
```

or using docker

```bash
docker run -d -p 7860:7860 -e MINERU_API_KEY=your_api_key registry.cn-hangzhou.aliyuncs.com/data_proc/mineru_app:v0.0.10
```


## Use Gradio App

Access http://127.0.0.1:7860 in your web browser

