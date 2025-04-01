import React from "react";
import { useAppDispatch } from "../app/hooks";
import { triggerAction } from "../data/modelSlice";

interface CustomButtonRendererProps {
  uischema: any;
}

export const CustomButtonRenderer: React.FC<CustomButtonRendererProps> = ({
  uischema,
}) => {
  const dispatch = useAppDispatch();
  const handleClick = () => {
    switch (uischema.onClick) {
      case "submit":
        dispatch(triggerAction("submit"));
        break;
      case "reset":
        dispatch(triggerAction("reset"));
        break;
      default:
        console.log("Unknown action chosen.");
    }
  };

  return (
    <button onClick={() => handleClick()} style={{ margin: "8px 0" }}>
      {uischema.label}
    </button>
  );
};
