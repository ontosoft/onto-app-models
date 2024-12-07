const runApplication = async () => {
    try {
        const response = await fetch("http://localhost:8089/run_application");
        const data = await response.json();
        console.log(data);
        //setLoadedModelInfo(JSON.parse(data));
    } catch (error) {
        console.error("Failed to load inner server models", error);
    }
}