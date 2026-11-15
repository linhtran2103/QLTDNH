
document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // 1. CAU HINH CHUNG
    // ==========================================

    const currencyFormatter = new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND"
    });

    const TOKEN_KEY = "qltdnh_token";
    const USER_KEY = "qltdnh_user";

    let allFoods = [];
    let allCategories = [];

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function getUser() {
        try {
            return JSON.parse(localStorage.getItem(USER_KEY) || "null");
        } catch {
            return null;
        }
    }

    function getHeaders(json = true) {
        const headers = {};

        if (json) {
            headers["Content-Type"] = "application/json";
        }

        const token = getToken();

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        return headers;
    }

    async function apiRequest(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...getHeaders(),
                ...(options.headers || {})
            }
        });

        let result;

        try {
            result = await response.json();
        } catch {
            throw new Error("Máy chủ trả về dữ liệu không hợp lệ.");
        }

        if (response.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);

            if (!window.location.pathname.includes("/login")) {
                alert("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
                window.location.href = "/login";
            }

            throw new Error(result.message || "Bạn cần đăng nhập lại.");
        }

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Có lỗi xảy ra.");
        }

        return result;
    }

    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;"
            }[char];
        });
    }

    function isActive(value) {
        return value === true || value === 1 || value === "1";
    }


    // ==========================================
    // 2. DANH SACH MON AN
    // ==========================================

    const foodTableBody = document.getElementById("foodTableBody");
    const foodSearch = document.getElementById("foodSearch");
    const categoryFilter = document.getElementById("categoryFilter");
    const statusFilter = document.getElementById("statusFilter");

    const totalFoods = document.getElementById("totalFoods");
    const availableFoods = document.getElementById("availableFoods");
    const unavailableFoods = document.getElementById("unavailableFoods");
    const totalCategories = document.getElementById("totalCategories");
    const resultCount = document.getElementById("resultCount");

    async function loadFoods() {
        if (!foodTableBody) return;

        try {
            const result = await apiRequest("/api/mon-an");

            allFoods = result.data || [];

            updateStatistics();
            loadCategoryFilter();
            filterFoods();

        } catch (error) {
            console.error("Lỗi tải món ăn:", error);

            foodTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger py-4">
                        ${escapeHTML(error.message)}
                    </td>
                </tr>
            `;
        }
    }

    function updateStatistics() {
        const available = allFoods.filter(food =>
            isActive(food.ConKinhDoanh)
        ).length;

        if (totalFoods) {
            totalFoods.textContent = allFoods.length;
        }

        if (availableFoods) {
            availableFoods.textContent = available;
        }

        if (unavailableFoods) {
            unavailableFoods.textContent = allFoods.length - available;
        }

        if (totalCategories) {
            totalCategories.textContent = allCategories.length;
        }
    }

    function loadCategoryFilter() {
        if (!categoryFilter) return;

        const selected = categoryFilter.value;

        categoryFilter.replaceChildren();

        const first = document.createElement("option");
        first.value = "";
        first.textContent = "Tất cả danh mục";
        categoryFilter.appendChild(first);

        allCategories.forEach(category => {
            const option = document.createElement("option");

            option.value = category.MaDanhMuc;
            option.textContent = category.TenDanhMuc;

            categoryFilter.appendChild(option);
        });

        categoryFilter.value = selected;
    }

    function renderFoods(foods) {
        if (!foodTableBody) return;

        foodTableBody.replaceChildren();

        if (foods.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 6;
            cell.className = "text-center py-4";
            cell.textContent = "Không tìm thấy món ăn phù hợp.";

            row.appendChild(cell);
            foodTableBody.appendChild(row);
        }

        foods.forEach(food => {
            const row = document.createElement("tr");

            const values = [
                food.MaMon || "",
                food.TenMonAn || "",
                food.TenDanhMuc || "",
                currencyFormatter.format(Number(food.Gia) || 0)
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            const statusCell = document.createElement("td");
            const badge = document.createElement("span");

            const active = isActive(food.ConKinhDoanh);

            badge.className = active
                ? "badge bg-success"
                : "badge bg-danger";

            badge.textContent = active
                ? "Đang phục vụ"
                : "Ngừng phục vụ";

            statusCell.appendChild(badge);
            row.appendChild(statusCell);

            const actionCell = document.createElement("td");
            const editLink = document.createElement("a");

            editLink.href = `/foods/edit/${food.MaMonAn}`;
            editLink.className = "btn btn-sm btn-outline-primary";
            editLink.textContent = "Sửa";

            actionCell.appendChild(editLink);
            row.appendChild(actionCell);

            foodTableBody.appendChild(row);
        });

        if (resultCount) {
            resultCount.textContent =
                `Hiển thị ${foods.length} / ${allFoods.length} món ăn`;
        }
    }

    function filterFoods() {
        const keyword = foodSearch?.value.trim().toLowerCase() || "";
        const category = categoryFilter?.value || "";
        const status = statusFilter?.value || "";

        const filtered = allFoods.filter(food => {
            const name = (food.TenMonAn || "").toLowerCase();
            const code = (food.MaMon || "").toLowerCase();

            const matchesName =
                name.includes(keyword) || code.includes(keyword);

            const matchesCategory =
                !category || String(food.MaDanhMuc) === category;

            const active = isActive(food.ConKinhDoanh);

            const matchesStatus =
                !status ||
                (status === "available" && active) ||
                (status === "unavailable" && !active);

            return matchesName && matchesCategory && matchesStatus;
        });

        renderFoods(filtered);
    }

    foodSearch?.addEventListener("input", filterFoods);
    categoryFilter?.addEventListener("change", filterFoods);
    statusFilter?.addEventListener("change", filterFoods);


    // ==========================================
    // 3. TAI DANH MUC
    // ==========================================

    async function fetchCategories() {
        const result = await apiRequest("/api/danh-muc?trang_thai=true");

        allCategories = result.data || [];

        updateStatistics();
        loadCategoryFilter();

        return allCategories;
    }

    async function loadCategories(selectElement, selectedId = "") {
        if (!selectElement) return;

        if (allCategories.length === 0) {
            await fetchCategories();
        }

        selectElement.replaceChildren();

        const first = document.createElement("option");
        first.value = "";
        first.textContent = "Chọn danh mục";

        selectElement.appendChild(first);

        allCategories.forEach(category => {
            const option = document.createElement("option");

            option.value = category.MaDanhMuc;
            option.textContent = category.TenDanhMuc;

            selectElement.appendChild(option);
        });

        selectElement.value = String(selectedId);
    }

    const addCategory = document.getElementById("foodCategory");

    if (foodTableBody || addCategory || document.getElementById("editFoodForm")) {
        fetchCategories().catch(error => {
            console.error("Lỗi tải danh mục:", error);
        });
    }

    if (foodTableBody) {
        loadFoods();
    }

    if (addCategory && !document.getElementById("editFoodForm")) {
        loadCategories(addCategory).catch(error => {
            console.error(error);
            alert("Không thể tải danh mục: " + error.message);
        });
    }


    // ==========================================
    // 4. XEM TRUOC ANH
    // ==========================================

    function setupImagePreview(inputId, previewId, removeId) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        const remove = document.getElementById(removeId);

        if (!input || !preview) return;

        let objectURL = null;

        input.addEventListener("change", function () {
            const file = this.files[0];

            if (!file) return;

            if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
                alert("Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP.");
                this.value = "";
                return;
            }

            if (file.size > 5 * 1024 * 1024) {
                alert("Ảnh không được vượt quá 5MB.");
                this.value = "";
                return;
            }

            if (objectURL) {
                URL.revokeObjectURL(objectURL);
            }

            objectURL = URL.createObjectURL(file);

            preview.src = objectURL;
            preview.style.display = "block";

            if (remove) {
                remove.hidden = false;
            }
        });

        remove?.addEventListener("click", function () {
            input.value = "";
            preview.src = "";
            preview.style.display = "none";
            remove.hidden = true;

            if (objectURL) {
                URL.revokeObjectURL(objectURL);
                objectURL = null;
            }
        });
    }

    setupImagePreview("foodImage", "imagePreview", "removeImage");

    setupImagePreview(
        "editFoodImage",
        "editImagePreview",
        "removeEditImage"
    );


    // ==========================================
    // 5. THEM MON AN
    // ==========================================

    const addForm = document.getElementById("addFoodForm");
    const saveButton = document.getElementById("saveFoodButton");

    if (addForm) {
        addForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const codeInput = document.getElementById("foodCode");
            const nameInput = document.getElementById("foodName");
            const categoryInput = document.getElementById("foodCategory");
            const priceInput = document.getElementById("foodPrice");
            const descriptionInput = document.getElementById("foodDescription");

            const code = codeInput?.value.trim() || "";
            const name = nameInput?.value.trim() || "";
            const category = categoryInput?.value || "";
            const price = Number(priceInput?.value);
            const description = descriptionInput?.value.trim() || "";

            if (!code || !name || !category ||
                !Number.isFinite(price) || price < 0) {
                alert("Vui lòng nhập mã món, tên món, danh mục và giá hợp lệ.");
                return;
            }

            if (!getToken()) {
                alert("Bạn cần đăng nhập để thêm món ăn.");
                window.location.href = "/login";
                return;
            }

            if (saveButton) {
                saveButton.disabled = true;
                saveButton.textContent = "Đang lưu...";
            }

            try {
                const result = await apiRequest("/api/mon-an", {
                    method: "POST",
                    body: JSON.stringify({
                        MaMon: code,
                        TenMonAn: name,
                        MaDanhMuc: Number(category),
                        Gia: price,
                        MoTa: description,
                        HinhAnh: null
                    })
                });

                alert(result.message || "Thêm món ăn thành công!");
                window.location.href = "/foods";

            } catch (error) {
                console.error(error);
                alert(error.message);

            } finally {
                if (saveButton) {
                    saveButton.disabled = false;
                    saveButton.textContent = "Lưu món ăn";
                }
            }
        });
    }


    // ==========================================
    // 6. SUA MON AN
    // ==========================================

    const editForm = document.getElementById("editFoodForm");

    if (editForm) {
        const foodId = Number(
            window.location.pathname.split("/").pop()
        );

        const nameInput = document.getElementById("foodName");
        const categoryInput = document.getElementById("foodCategory");
        const priceInput = document.getElementById("foodPrice");
        const descriptionInput = document.getElementById("foodDescription");
        const codeInput = document.getElementById("foodCode");

        let currentImageURL = null;

        async function loadFoodDetail() {
            try {
                const result = await apiRequest("/api/mon-an");

                const foods = result.data || [];

                const food = foods.find(item =>
                    Number(item.MaMonAn) === foodId
                );

                if (!food) {
                    throw new Error("Không tìm thấy món ăn.");
                }

                if (nameInput) {
                    nameInput.value = food.TenMonAn || "";
                }

                if (priceInput) {
                    priceInput.value = food.Gia ?? "";
                }

                if (descriptionInput) {
                    descriptionInput.value = food.MoTa || "";
                }

                if (codeInput) {
                    codeInput.value = food.MaMon || "";
                }

                await loadCategories(
                    categoryInput,
                    food.MaDanhMuc
                );

                currentImageURL = food.HinhAnh || "";

                const preview = document.getElementById("editImagePreview");

                if (preview && currentImageURL) {
                    preview.src = currentImageURL;
                    preview.style.display = "block";
                }

            } catch (error) {
                console.error("Lỗi tải chi tiết món ăn:", error);
                alert(error.message);
            }
        }

        loadFoodDetail();

        editForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const name = nameInput?.value.trim() || "";
            const category = categoryInput?.value || "";
            const price = Number(priceInput?.value);

            if (!name || !category ||
                !Number.isFinite(price) || price < 0) {
                alert("Vui lòng nhập tên, danh mục và giá hợp lệ.");
                return;
            }

            if (!getToken()) {
                alert("Bạn cần đăng nhập để sửa món ăn.");
                window.location.href = "/login";
                return;
            }

            const button = editForm.querySelector('button[type="submit"]');

            if (button) {
                button.disabled = true;
                button.textContent = "Đang cập nhật...";
            }

            try {
                const result = await apiRequest(`/api/mon-an/${foodId}`, {
                    method: "PUT",
                    body: JSON.stringify({
                        TenMonAn: name,
                        MaDanhMuc: Number(category),
                        Gia: price,
                        MoTa: descriptionInput?.value.trim() || "",
                        HinhAnh: currentImageURL
                    })
                });

                alert(result.message || "Cập nhật món ăn thành công!");
                window.location.href = "/foods";

            } catch (error) {
                console.error(error);
                alert(error.message);

            } finally {
                if (button) {
                    button.disabled = false;
                    button.textContent = "Lưu thay đổi";
                }
            }
        });
    }


    // ==========================================
    // 7. DANG NHAP
    // ==========================================

    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const usernameInput =
                document.getElementById("username") ||
                document.getElementById("TenDangNhap");

            const passwordInput =
                document.getElementById("password") ||
                document.getElementById("MatKhau");

            const username = usernameInput?.value.trim() || "";
            const password = passwordInput?.value || "";

            if (!username || !password) {
                alert("Vui lòng nhập tên đăng nhập và mật khẩu.");
                return;
            }

            const button = loginForm.querySelector('button[type="submit"]');

            if (button) {
                button.disabled = true;
                button.textContent = "Đang đăng nhập...";
            }

            try {
                const result = await apiRequest("/api/dang-nhap", {
                    method: "POST",
                    body: JSON.stringify({
                        TenDangNhap: username,
                        MatKhau: password
                    })
                });

                localStorage.setItem(TOKEN_KEY, result.token);
                localStorage.setItem(USER_KEY, JSON.stringify(result.data));

                alert(result.message || "Đăng nhập thành công!");
                window.location.href = "/";

            } catch (error) {
                console.error(error);
                alert(error.message);

            } finally {
                if (button) {
                    button.disabled = false;
                    button.textContent = "Đăng nhập";
                }
            }
        });
    }


    // ==========================================
    // 8. DANG XUAT
    // ==========================================

    document.querySelectorAll("[data-logout]").forEach(button => {
        button.addEventListener("click", function () {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);

            window.location.href = "/login";
        });
    });


    // ==========================================
    // 9. HIEN THI THONG TIN NGUOI DUNG
    // ==========================================

    const currentUser = getUser();

    if (currentUser) {
        document.querySelectorAll("[data-user-name]").forEach(element => {
            element.textContent = currentUser.HoTen || currentUser.TenDangNhap;
        });

        document.querySelectorAll("[data-user-role]").forEach(element => {
            element.textContent = currentUser.VaiTro || "";
        });
    }

});


// ==========================================
// 10. CHUC NANG CHUA PHAT TRIEN
// ==========================================

function showComingSoon() {
    alert("Chức năng đang được phát triển.");
}
