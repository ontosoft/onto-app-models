import { Component } from "react";
import Navbar from "./Navbar";
import { ModelNavigator } from "./generator/ModelNavigator";
import { ModelPresenter } from "./generator/ModelPresenter";
import { UIDisplay } from "./generator/UIDisplay";
//import "./App.css";
import "./Navbar.css";

export default class App extends Component {
  render() {
    return (
      <>
        <Navbar />
        <div className="container-fluid">
          <div className="row">
            <ModelNavigator />
            <UIDisplay />
          </div>
        </div>
          <ModelPresenter />
      </>
    );
  }
}
