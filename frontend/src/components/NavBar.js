import React from 'react';
import './NavBar.css';
var NavBar = function () {
    return (<nav className="navbar">
      <div className="navbar-logo">
        NRE Sovereign Dashboard
      </div>
      <ul className="navbar-links">
        <li><a href="/">Overview</a></li>
        <li><a href="/agents">Agents</a></li>
        <li><a href="/memory">Memory</a></li>
        <li><a href="/settings">Settings</a></li>
      </ul>
    </nav>);
};
export default NavBar;
