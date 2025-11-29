# ComicMeta Editor

ComicMeta Editor 是一个基于 PySide6 开发的漫画元数据编辑器，为管理和整理Komga本地漫画收藏而设计。它支持 `.zip` 和 `.cbz` 格式，并提供简易的元数据刮削功能。

## 主要功能

*   **元数据编辑**：支持编辑标题、作者、系列、卷号、标签等多种元数据。
*   **自动刮削**：集成 Bangumi (bgm.tv) API，自动获取漫画信息。
*   **批量操作**：支持批量重命名、批量应用元数据。
*   **格式转换**：支持 zip 和 cbz 格式互转。
*   **多语言支持**：内置中、英、日多语言界面。
*   **现代化 UI**：基于 PySide6 的现代化暗色主题界面。

## 安装与运行

### 源码运行

1.  克隆仓库：
    ```bash
    git clone https://github.com/您的用户名/ComicMetaEditor.git
    cd ComicMetaEditor
    ```

2.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

3.  运行程序：
    ```bash
    python main.py
    ```

### 打包构建

### 打包构建

本项目提供了一个构建脚本，可以直接运行：

```bash
build.bat
```

或者手动运行 PyInstaller：

```bash
pyinstaller ComicMetaEditor.spec
```

## 致谢

本项目在开发过程中使用了 Gemini 3 与 Claude Sonnet 4.5 辅助编程。
