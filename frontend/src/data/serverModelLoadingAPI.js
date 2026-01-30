


const API_BASE_URL = process.env.REACT_APP_API_URL || "";
export const fetchListOfServerModels = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/read_inner_server_models`);
        const data = await response.json();
        console.log(data);
        return data;
    } catch (error) {
        console.error("Failed to load inner server models", error);
    }
};

