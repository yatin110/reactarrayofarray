// src/components/FormComponent.js
import React, { useState } from "react";

const FormComponent = () => {
  const [formData, setFormData] = useState({
    name: "",
    arrayOfArrays: [["", ""]], // Initialize with an array of arrays
  });

  // Handle change for simple input fields
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Handle change for array of arrays input
  const handleArrayChange = (index, subIndex, value) => {
    const updatedArray = [...formData.arrayOfArrays];
    updatedArray[index][subIndex] = value;
    setFormData({ ...formData, arrayOfArrays: updatedArray });
  };

  // Add a new row to the array of arrays
  const addRow = () => {
    setFormData({
      ...formData,
      arrayOfArrays: [...formData.arrayOfArrays, ["", ""]],
    });
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("Form Data as JSON:", JSON.stringify(formData, null, 2));
    // Store the JSON as needed (e.g., in localStorage or send to backend)
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Name:</label>
        <input
          type="text"
          name="name"
          value={formData.name}
          onChange={handleChange}
        />
      </div>
      
      <div>
        <h3>Array of Arrays</h3>
        {formData.arrayOfArrays.map((arr, index) => (
          <div key={index} style={{ marginBottom: "10px" }}>
            {arr.map((item, subIndex) => (
              <input
                key={subIndex}
                type="text"
                value={item}
                onChange={(e) =>
                  handleArrayChange(index, subIndex, e.target.value)
                }
                style={{ marginRight: "5px" }}
              />
            ))}
          </div>
        ))}
        <button type="button" onClick={addRow}>
          Add Row
        </button>
      </div>

      <button type="submit">Submit</button>
    </form>
  );
};

export default FormComponent;






// src/App.js
import React from "react";
import "./App.css";
import FormComponent from "./components/FormComponent";

function App() {
  return (
    <div className="App">
      <h1>Form with Array of Arrays</h1>
      <FormComponent />
    </div>
  );
}

export default App;





// src/components/FormComponent.js
import React from "react";
import Form from "@rjsf/core";

const schema = {
  title: "User Form",
  type: "object",
  required: ["name", "age", "friends"],
  properties: {
    name: {
      type: "string",
      title: "Name",
    },
    age: {
      type: "number",
      title: "Age",
    },
    friends: {
      type: "array",
      title: "Friends",
      items: {
        type: "string",
      },
    },
  },
};

const FormComponent = () => {
  const handleSubmit = ({ formData }) => {
    console.log("Form Data:", formData);
    // You can save the formData as JSON or send it to a backend
  };

  return (
    <div>
      <h2>Dynamic Form from JSON Schema</h2>
      <Form schema={schema} onSubmit={handleSubmit} />
    </div>
  );
};

export default FormComponent;


npm install @rjsf/validator-ajv8





// src/components/FormComponent.js
import React from "react";
import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";

const schema = {
  title: "User Form",
  type: "object",
  required: ["name", "age", "friends"],
  properties: {
    name: {
      type: "string",
      title: "Name",
    },
    age: {
      type: "number",
      title: "Age",
    },
    friends: {
      type: "array",
      title: "Friends",
      items: {
        type: "string",
        title: "Friend's Name",
      },
      minItems: 1, // You can specify minItems to ensure at least one friend is added
    },
  },
};

const uiSchema = {
  friends: {
    "ui:options": {
      addable: true, // Allow adding more items
      orderable: true, // Allow reordering items
      removable: true, // Allow removing items
    },
  },
};

const FormComponent = () => {
  const handleSubmit = ({ formData }) => {
    console.log("Form Data:", formData);
  };

  return (
    <div>
      <h2>Dynamic Form from JSON Schema</h2>
      <Form
        schema={schema}
        uiSchema={uiSchema}
        validator={validator}
        onSubmit={handleSubmit}
      />
    </div>
  );
};

export default FormComponent;
