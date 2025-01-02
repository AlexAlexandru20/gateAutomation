function showPassword(){
    var password = document.getElementById("password");
    var is_checked = document.getElementById("exampleCheck");
    if (is_checked.checked){
        password.type = 'text';
    }
    else{
        password.type = 'password';
    }
}
function showPassword_reset(){
    var password = document.getElementById("password_reset");
    var is_checked = document.getElementById("exampleCheck_reset");
    if(is_checked.checked){
        password.type = 'text';
    }
    else{
        password.type = 'password';
    }
}
function showPassword_confirm(){
    var password = document.getElementById("password_confirm");
    var is_checked = document.getElementById("exampleCheck_confirm");
    if(is_checked.checked){
        password.type = 'text';
    }
    else{
        password.type = 'password';
    }
}
