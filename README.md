# email-signatures
Contains the necessary data and code to generate the email signature of the managed employees in EHS.

## Components
###### Bulk update of secrets
We use `gh` CLI utility to read from a secret file that creates all of our organization secrets in bulk.

###### Secrets
The real data for the signatures are stored as GitHub secrets in the [EHS organization](https://github.com/Equipaments-Hosteleria-Salou).
Each secret belongs to the person with the same initial in its name. This is for privacy reasons. Secrets are used in 
the [GitHub Actions workflow](https://github.com/Equipaments-Hosteleria-Salou/email-signatures/actions).

To add a new signature you will need to define the secrets for the personal data of that employee in the 
[organization secrets](https://github.com/organizations/Equipaments-Hosteleria-Salou/settings/secrets/actions).

###### Data files
Data for signatures is defined in the `data` folder in JSON format. The data files are the files that are used by the 
templating engines to expand the marks in the template for the signature. 

The algorithm to substitute the marks in the data files in **dynamic**, so there is no need to change the code if adding
new signatures. 

To execute the algorithm to substitute marks you will need to run:
```shell
./substituteMarks.sh
```

This script is **idempotent**, and **it does not rely on relative paths**. It uses environment variables as implicit 
parameters.

###### Template
The template for all the signatures is defined in the `template` folder. The template is valid for all signatures. No 
need to modify it to add a new signature. The template is written in HTML and uses the image stored in [this public 
repository](https://github.com/Equipaments-Hosteleria-Salou/simple-image-hosting) to obtain the images for the 
signature.

The template is designed to be used with [Handlebars](https://handlebarsjs.com/).

###### Template render
To render the template you need to execute the JavaScript file `renderSignatures.js` in the `src` folder of this 
repository. You will need to install `npm` and `node`. This will vary in each operating system, but usually the best 
way is to [download the pre-built binaries](https://nodejs.org/en/download/prebuilt-binaries) or install [using the 
package manager](https://nodejs.org/en/download/package-manager). 

After that you need to install handlebars directly:
```shell
npm install handlebars
```

... or using the `package.json`:
```shell
cd email-signatures && npm install
```

After that, to execute the script you can do: 
```shell
node ./src/renderSignatures.js
```

The template renderer script is **dynamic**, which means that there is no need to change the code of the script to 
render new signatures. The script produces a signatures for each file in the `data` folder.

###### Template output
The output of the program is in the `out` folder. This folder is ignored because it contains the personal data of each 
signature. 

###### Email sending
We are using the [action-send-email](https://github.com/dawidd6/action-send-mail) from [@dawidd6](https://github.com/dawidd6).
You will need to configure an email account to be able to send the emails. For a Gmail account you need to configure an 
App password in you Google account. Here are the steps:

1. [Enable 2-Step Verification.](https://support.google.com/accounts/answer/185839?hl=en&co=GENIE.Platform%3DAndroid).
   This is needed to create an App password.
2. [Create an App password](https://support.google.com/accounts/answer/185833?hl=en) for `Mail`.

###### Workflow
All steps are triggered in a GitHub Actions Workflow:
- Secrets are read and injected as environment variables of the workflow. 
- Environment variables are used to translate the marks into personal data of files in the `data` folder.
- Data files are used as input for the template to build the signatures.
- Signatures are sent to each respective owner.

There is a workflow for each managed signature that is triggered when that signature is modified. 

If there is the need to add a new signature you need a workflow that manages that signature.

## Usage
###### Adding a new signature
- Create the secrets in the organization N_NAME, N_EMAIL, N_PHONE and N_IPHONE, which are the name, the email, the phone 
  and the phone with international prefix (without spaces to generate a proper `mailto:` link), where N is the initial 
  or 
  another string that identifies the person but without revealing any of its personal data.
- Create the file `N.json` in the `data` folder. N needs to be the same.
- Create the workflow `sendSignatureToN.yml` that is configured to send the signature to its owner and is triggered only
  when the signature is modified.
- Add the files, commit and push to GitHub to trigger the workflow.

###### Updating a signature
- Change the data files to trigger the build and send of the updated signature. 

Since the workflow is only triggered 
when the signature is updated, you can add a meaningless change in the data file of the signature such as adding a 
whitespace or a line break.

###### Updating all signatures
- Change the template to trigger the build and send of all signatures.

Since the workflow is only triggered
when the signature is updated, you can add a meaningless change in the data file of the signature such as adding a
whitespace or a line break to trigger the workflow and receive the signatures in your email.

## Roadmap
This project is completely functional! But there is still some space for improvements...
- Convert workflows into a template that can be customized. This way we will reduce duplication since workflows are more 
or less all the same. This means that we will have a workflow template and a script that receives some data and combines
them into a workflow file that manages a certain signature.
- Refactor bash script, so it only translates the variables of the needed files.
- Refactor templating script, so it only creates the signature that is needed.
- A way to easily update and add signatures without the need to touching workflows, files, etc.

## Acknowledgements
Shout out to [@Bpazg97](https://github.com/Bpazg97) who suggested the usage of HandleBars which suited the job 
perfectly.  





# some commands that I used in this fork
wkhtmltopdf --enable-local-file-access --margin-right 0 --margin-left 0 --margin-bottom 0 --margin-top 0 --orientation Landscape --page-size A4 templates/certificate/raw_template.html mypage.pdf