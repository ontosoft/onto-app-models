import React, { Fragment, useState, createContext, useContext} from "react";
import { Form } from "./Form";


const ThemeContext = createContext(null);


interface FormJSXProps {
    node: string;
    target_classes: [];
    elements: {};
}


const getDefaultLayout = (layout_type:string, data: unknown): React.JSX.Element => {
    return (
      <div>
        <h1>Default Layout</h1>
      </div >
    );
}

const handleSubmit = (e: string) => {
    console.log(e);
}

function Panel({ title, children }: { title: string, children: React.ReactNode }) {
    const theme = useContext(ThemeContext);
    const className = 'panel-' + theme;
    return (
      <section className={className}>
        <h1>{title}</h1>
        {children}
      </section>
    )
}

const FormComponent = (formProps: FormJSXProps): React.JSX.Element => {
    const [field1, setField1] = useState("");
    const formName:string = formProps.node;
    
    console.log("Form node is", formName)
    return (
        //<Panel title={""}>
        <form>
            <div>
                <h1>{formName}</h1>
                <label htmlFor="field"></label>
                <input
                    type="text"
                    id="field1"
                    value={field1}
                    onChange={(e) => setField1(e.target.value)}
                />
            </div>
            <button type="submit" onClick={() => handleSubmit(field1)}>Submit</button>
        </form>
       // </Panel>
    );
}

const LabelJSX = ({ label, input }: { label: string, input: string }): JSX.Element => {
    return (
           <label htmlFor= "field1" > { label } </label>
    );
}

const ImageJSX = ({ src, url, alt, caption }: { src: string, url: string, alt: string, caption: string }): JSX.Element => {
    return (
        <a href={url}>
          caption={caption}
        </a>
    );
}


export { FormComponent, getDefaultLayout, LabelJSX, ImageJSX };
export type { FormJSXProps };