import React from 'react';
import ReactDOM from 'react-dom/client';
import './css/index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import 'bootstrap/dist/css/bootstrap.min.css';
import Modal from 'react-modal';

// Configurar el elemento raíz para react-modal
Modal.setAppElement('#root');

const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
  document.documentElement.classList.add('theme-dark');
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
