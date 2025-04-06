<p align="center">
  <img src="resource/images/logo.ico" width="100" height="100" style="vertical-align: middle;" />
</p>
<h1 align="center">SmartMemo</h1>

<p align="center">
一个基于PyQt5及PyQt-Fluent-Widgets的智能备忘录管理系统
</p>

## 系统简介

本系统是一个**智能化、安全可靠**的备忘录管理工具。用户可以使用本系统来管理自己的备忘录以及待办事项。系统包含备忘录管理功能，待办事项管理功能，以及AI交互功能等多方面功能，能为用户提供智能、高效的备忘录管理体验。

## 快速开始🚀

+ 方式1：直接运行Smart-Memo-Manager打包后的可执行程序（推荐） 

  [下载](https://github.com/tingyuPP/Smart-Memo-Manager/releases/tag/release)并解压`Smart-Memo-Manager.zip`后双击`main.exe`即可运行。

+ 方式2：通过源码运行
```shell
# 首先克隆仓库代码
git clone https://github.com/tingyuPP/Smart-Memo-Manager.git

# 进入项目目录
cd Smart-Memo-Manager

# 创建Python 3.12虚拟环境，以VENV为例，也可使用conda等
python -m venv Smart-Memo-Manager-VENV

# 激活虚拟环境后安装依赖
pip install -r requirements.txt		

# 运行程序
python main.py
```

## 运行示例▶️

### 备忘录管理

<img src="resource\examples\memo.gif" alt="备忘录管理" />

### AI自动补全

<img src="resource\examples\completion.gif" alt="AI自动补全" />

### AI一键生成文案

<img src="resource\examples\generate.gif" alt="AI一键生成文案" />

### AI自动提取待办事项

<img src="resource\examples\todo_extractor.gif" alt="AI自动提取待办事项" />

### 待办事项管理

<img src="resource\examples\todo.gif" alt="待办事项管理" />

### 个人信息管理

<img src="resource\examples\personal.gif" alt="个人信息管理" />

### 系统自定义设置

<img src="resource\examples\setting.gif" alt="系统自定义设置" />

## 项目特点🔥

- **简洁，美观的图形界面**：基于qfluentwidgets构建，界面简洁美观，便于用户操作。
- **智能助手加持**：将大模型融入笔记工具场景。用户能够在编辑备忘录时让大模型帮忙进行续写，润色等。还能让大模型从备忘录中自动提取
- **富文本支持**：用户能够使用markdown语法编辑备忘录内容，功能性更强大。
- **加密保障**：使用AES-256加密算法和哈希算法保障用户数据安全，确保用户隐私不泄露。

## 参考👀

- https://qfluentwidgets.com/
