## 安装


```bash
pip install mineru_app
```

或使用 docker 

```bash
docker pull registry.cn-hangzhou.aliyuncs.com/data_proc/mineru_app:v0.0.10
```

## 启动

请先去 [mineru官网](https://mineru.net/apiManage/docs) 申请 api key

```bash
export MINERU_API_KEY=your_api_key
mineru_app
```

或使用 docker

```bash
docker run -d -p 7860:7860 -e MINERU_API_KEY=your_api_key registry.cn-hangzhou.aliyuncs.com/data_proc/mineru_app:v0.0.10
```


## 访问

在浏览器中打开 http://127.0.0.1:7860 
