import React from "react";
import logo from "./ontoui_logo.min.svg";

import "./Navbar.css";

const Navbar = () => {
  return (
    <div className="header">
      <img src={logo} className="logo" alt="logo" />
      <div className="navbar"></div>
    </div>
  );
};

export default Navbar;
