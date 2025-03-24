
export const fetchListOfServerModels = async () => {
    try {
        const response = await fetch("http://localhost:8089/read_inner_server_models");
        const data = await response.json();
        console.log(data);
        return JSON.parse(data)
    } catch (error) {
        console.error("Failed to load inner server models", error);
    }
};

