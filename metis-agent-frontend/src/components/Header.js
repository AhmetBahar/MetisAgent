import React from 'react';
import { Menu, Bell, User } from 'lucide-react';
import MetisAgentLogo from '../MetisAgent.png';
import './Header.css';

const Header = ({ toggleSidebar }) => {
  return (
    <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-4">
      <div className="flex items-center space-x-3">
        <button 
          onClick={toggleSidebar}
          className="p-2 rounded-md hover:bg-gray-100"
        >
          <Menu size={20} />
        </button>
        <div className="flex items-center space-x-2">
          <img 
            src={MetisAgentLogo} 
            alt="MetisAgent" 
            className="w-8 h-8 rounded-md shadow-sm"
          />
          <h1 className="text-xl font-bold text-gray-800">Metis Agent</h1>
        </div>
      </div>
      <div className="flex items-center space-x-4">
        <button className="p-2 rounded-full hover:bg-gray-100">
          <Bell size={20} />
        </button>
        <div className="flex items-center">
          <span className="mr-2 hidden md:block">Admin</span>
          <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
            <User size={16} />
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;