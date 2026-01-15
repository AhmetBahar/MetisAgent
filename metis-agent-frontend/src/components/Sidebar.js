// src/components/Sidebar.js
import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Home, Files, Users, Network, Calendar, 
  Archive, Edit, Settings, MessageSquare, PlayCircle
} from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ isOpen }) => {
  const menuItems = [
    { name: 'Dashboard', path: '/', icon: <Home size={20} /> },
    { name: 'File Manager', path: '/files', icon: <Files size={20} /> },
    { name: 'User Manager', path: '/users', icon: <Users size={20} /> },
    { name: 'Network Manager', path: '/network', icon: <Network size={20} /> },
    { name: 'Scheduler', path: '/scheduler', icon: <Calendar size={20} /> },
    { name: 'Archive Manager', path: '/archives', icon: <Archive size={20} /> },
    { name: 'Editor', path: '/editor', icon: <Edit size={20} /> },
    { name: 'Chat', path: '/chat', icon: <MessageSquare size={20} /> },
    { name: 'Task Runner', path: '/tasks', icon: <PlayCircle size={20} /> },
    { name: 'Settings', path: '/settings', icon: <Settings size={20} /> },
  ];

  return (
    <div className={`${isOpen ? 'w-64' : 'w-20'} duration-300 h-screen bg-gray-800 text-white p-4 transition-all`}>
      <div className="flex items-center justify-center mb-8">
        <h1 className={`${isOpen ? 'block' : 'hidden'} text-xl font-bold`}>Metis Agent</h1>
        <img src="/logo192.png" alt="Metis" className={`${isOpen ? 'hidden' : 'block'} w-10 h-10`} />
      </div>
      <nav>
        <ul>
          {menuItems.map((item) => (
            <li key={item.name} className="mb-2">
              <NavLink
                to={item.path}
                className={({ isActive }) => 
                  `flex items-center p-2 rounded-lg ${isActive ? 'bg-blue-600' : 'hover:bg-gray-700'}`
                }
              >
                <span className="mr-3">{item.icon}</span>
                <span className={`${isOpen ? 'block' : 'hidden'}`}>{item.name}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar;