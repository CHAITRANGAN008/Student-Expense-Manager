# Student-Expense-Manager

# 💰 Student Expense Manager

A modern, feature-rich desktop application designed to help students track their daily expenses, manage budgets, analyze spending habits, and monitor their personal finances — all locally and privately.

Built with Python and SQLite, featuring a premium desktop interface and detailed PDF financial reports.

## ✨ Features

### 📊 Interactive Dashboard

- Overview of total balance, income, and expenses.
- Monthly financial summaries.
- Recent transaction history.
- Interactive financial charts.
- Online vs. offline spending overview.

### 💳 Transaction Management

- Add, edit, and delete transactions.
- Track both income and expenses.
- Categorize transactions.
- Separate online and offline payments.
- Record payment methods and descriptions.
- Search and filter transaction history.

### 🎯 Budget Management

- Set monthly spending budgets.
- Create category-wise budgets.
- Monitor budget utilization.
- Track remaining budget.
- Visual budget progress indicators.

### 📈 Spending Analytics

- Monthly spending trends.
- Category-wise expense analysis.
- Income vs. expense comparisons.
- Online vs. offline spending analysis.
- Payment method distribution.

### 📄 PDF Reports

- Generate monthly financial reports.
- Export custom date-range reports.
- Category-wise spending summaries.
- Budget utilization reports.
- Detailed transaction records.
- Professional PDF formatting.
- Save and print generated reports.

### 🔒 Local Data Storage

- SQLite-based database.
- No cloud dependency.
- No account registration required.
- Works offline.
- Personal financial data stays on your device.

### 🎨 Modern User Interface

- Premium desktop interface.
- Dark and light theme support.
- Interactive navigation.
- Modern dashboard cards.
- Attractive charts and visualizations.
- Clean and responsive layouts.

---

## 🛠️ Tech Stack

| Technology   | Purpose                     |
| ------------ | --------------------------- |
| Python       | Core application logic      |
| PySide6      | Desktop graphical interface |
| SQLite       | Local database              |
| Matplotlib   | Data visualization          |
| ReportLab    | PDF report generation       |
| Platformdirs | Application data management |

---


## ⚙️ Installation

### Prerequisites

- Windows 10/11
- Python 3.12 or newer
- Git (optional)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
python main.py
```

---

## 🏗️ Project Architecture

The application follows a modular architecture that separates the user interface, business logic, and database operations.

```text
Student-Expense-Manager/
│
├── main.py
├── requirements.txt
│
├── app/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   └── ui/
│
├── tests/
│
└── README.md
```

---

## 🗄️ Data Storage

The application uses SQLite for persistent local storage.

Financial information is stored on the user's device, without requiring a remote database or cloud account.

The application supports:

- Transaction records
- Income and expense categories
- Monthly budgets
- Financial summaries

**Privacy-first approach:** Your personal financial data is not intended to be uploaded to external servers.

---

## 🚀 Future Improvements

Potential future enhancements:

- [ ] Automatic recurring transactions
- [ ] Receipt image attachments
- [ ] Advanced financial insights
- [ ] More detailed PDF customization
- [ ] Database encryption
- [ ] Application installer
- [ ] Improved backup and restore functionality

---

## 🎯 Project Motivation

Managing money as a student can be challenging.

Small daily expenses such as food, transportation, shopping, subscriptions, and other purchases can accumulate without us noticing.

This project aims to make personal expense management simple, organized, and insightful through a dedicated desktop application.

It is also a practical exploration of desktop application development, database management, software architecture, and data visualization.

---

## 🤝 Contributing

Suggestions, bug reports, and contributions are welcome!

Feel free to fork the repository and submit a pull request.

---

---

**Built with ❤️ for smarter student money management.**
