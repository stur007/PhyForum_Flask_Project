# 🌐 PhyForum - A Simple Web Platform for Posts and Comments

**PhyForum** is a personal full-stack web project designed to facilitate scientific discussion through user registration, post creation, threaded comments, and profile customization. Built with modern tools and aided by AI-powered resources (like ChatGPT and DeepSeek), this platform reflects my exploration of web development’s expansive possibilities. Currently in active development, PhyForum’s prototype is live at [PhyForum](https://phyforum.onrender.com/)—feedback and contributions are warmly welcomed!

## 🛠️ Features

- 📝 Create, edit, and delete posts and comments (with proper permission control)
- 🔐 User authentication with email verification
- 📬 Real email required for registration
- 👤 Personal profile page with the ability to delete account

## 🚀 Future Plans

We are actively working to improve the project. Here are some planned features:

- 🖼️ **Add users' avatars**  
  Allow users to upload and display personalized profile pictures.
- 👍 **Add like button**  
  Enable users to like posts and show popularity.
- 🗂️ **Classify the posts**  
  Implement post categorization for easier navigation and filtering.


## 🧪 Setup Instructions

> Adjust commands to your environment.

```bash
git clone https://github.com/stur007/PhyForum_Flask_Project.git
cd PhyForum_Flask_Project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=app.py
export FLASK_ENV=development

flask db init
flask db migrate
flask db upgrade

flask run
```
## 📄 Changelog
See the full update history in [CHANGELOG.md](./CHANGELOG.md).

## 📮 Contact
For questions or feedback, please contact:
📧 [yutongren45@gmail.com](mailto:yutongren45@gmail.com)