package de.rgzm.alligator.config;

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import org.json.simple.JSONObject;

/**
 * Class for POM details
 * @author thiery
 */
public class POM {
    
    /**
     * get POM info as JSON
     * @return pom JSON
     * @throws IOException 
     */
    public static JSONObject getInfo() throws IOException {
        JSONObject outObj = new JSONObject();
        JSONObject maven = new JSONObject();
        maven.put("modelVersion", ConfigProperties.getPropertyParam("modelVersion"));
        outObj.put("maven", maven);
        JSONObject project = new JSONObject();
        project.put("buildNumber", ConfigProperties.getPropertyParam("buildNumber"));
        project.put("buildNumberShort", ConfigProperties.getPropertyParam("buildNumber").substring(0, 7));
        project.put("buildRepository", ConfigProperties.getPropertyParam("url").replace(".git", "/tree/" + ConfigProperties.getPropertyParam("buildNumber")));
        project.put("artifactId", ConfigProperties.getPropertyParam("artifactId"));
        project.put("groupId", ConfigProperties.getPropertyParam("groupId"));
        project.put("version", ConfigProperties.getPropertyParam("version"));
        project.put("packaging", ConfigProperties.getPropertyParam("packaging"));
        project.put("name", ConfigProperties.getPropertyParam("name"));
        project.put("description", ConfigProperties.getPropertyParam("description"));
        project.put("url", ConfigProperties.getPropertyParam("url"));
        project.put("encoding", ConfigProperties.getPropertyParam("sourceEncoding"));
        project.put("doi", "10.5281/zenodo.2540709");
        project.put("developer", "Florian Thiery");
        project.put("metadata", "https://github.com/RGZM/alligator/blob/master/CITATION.cff");
        JSONObject warObject = new JSONObject();
        File file = new File(POM.class.getClassLoader().getResource("config.properties").getFile());
        SimpleDateFormat sdf = new SimpleDateFormat("dd/MM/yyyy HH:mm:ss");
        warObject.put("last build", sdf.format(file.lastModified()));
        outObj.put("war", warObject);
        outObj.put("project", project);
        return outObj;
    }

}
