package de.rgzm.alligator.restconfig;

import de.rgzm.alligator.config.ConfigProperties;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.ws.rs.container.ContainerRequestContext;
import javax.ws.rs.container.ContainerResponseContext;
import javax.ws.rs.container.ContainerResponseFilter;

public class CORSFilter implements ContainerResponseFilter {

	@Override
	public void filter(ContainerRequestContext request, ContainerResponseContext response)
			throws IOException {
        String method = request.getMethod();
        try {
            if (method.equals("GET")) {
                response.getHeaders().add("Access-Control-Allow-Origin", ConfigProperties.getPropertyParam("get_origin"));
            } else {
                response.getHeaders().add("Access-Control-Allow-Origin", ConfigProperties.getPropertyParam("other_origin"));
            }
            response.getHeaders().add("Access-Control-Allow-Methods", "GET, POST, PUT");
            response.getHeaders().add("Access-Control-Allow-Headers", "Content-Type, Accept, Accept-Encoding");
            response.getHeaders().add("Access-Control-Allow-Credentials", "false");
        } catch (Exception ex) {
            Logger.getLogger(CORSFilter.class.getName()).log(Level.SEVERE, null, ex);
        }
        return;
		
	}

}
